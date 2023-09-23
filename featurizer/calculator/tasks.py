import itertools
import time
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional, Type

import pandas as pd
import pytz
import ray
from portion import Interval
from ray.dag import DAGNode
from ray.types import ObjectRef
from streamz import Stream

from featurizer.actors.cache_actor import get_cache_actor
from featurizer.blocks.blocks import Block, lookahead_shift, merge_asof_multi
from featurizer.data_definitions.data_source_definition import DataSourceDefinition
from featurizer.data_definitions.synthetic_data_source_definition import SyntheticDataSourceDefinition
from featurizer.features.feature_tree.feature_tree import Feature
from featurizer.featurizer_utils.featurizer_utils import merge_blocks
from featurizer.sql.db_actor import DbActor, get_db_actor
from featurizer.sql.feature_catalog.models import FeatureCatalog
from common.pandas import df_utils
from common.streamz.stream_utils import run_named_events_stream
from common.pandas.df_utils import is_ts_sorted, concat, sub_df_ts
from featurizer.storage.data_store_adapter.data_store_adapter import DataStoreAdapter


def context(feature_key: str, interval: Interval) -> Dict[str, Any]:
    return {'feature_key': feature_key, 'interval': interval}


def bind_and_cache(
    func: ray.remote_function.RemoteFunction,
    cache: Dict[str, Dict[Interval, Tuple[int, Optional[ObjectRef]]]],
    context: Dict[str, Any],
    **kwargs
) -> DAGNode:
    feature_key = context['feature_key']
    interval = context['interval']
    node = func.bind(context, **kwargs)
    if feature_key not in cache:
        cache[feature_key] = {interval: (1, None)}
    else:
        if interval in cache[feature_key]:
            ref_count = cache[feature_key][interval][0]
            ref = cache[feature_key][interval][1]
            cache[feature_key][interval] = (ref_count + 1, ref)
        else:
            cache[feature_key][interval] = (1, None)

    return node


def _get_from_cache(context: Dict[str, Any]) -> Tuple[Optional[pd.DataFrame], bool]:
    cache_actor = get_cache_actor()

    # this call decreases obj ref counter
    obj_ref, should_cache = ray.get(cache_actor.check_cache.remote(context))
    if obj_ref is None:
        return None, should_cache
    try:
        return ray.get(obj_ref), should_cache
    except Exception as e:
        # we may have ownership problems
        print(f'Unable to get cached obj by ref: {e}')
        return None, should_cache


# TODO cache task ref rather than obj itself so we dont't wait for it to be ready and avoid re-calculating same task
def _cache(obj: Any, context: Dict[str, Any]):
    cache_actor = get_cache_actor()
    obj_ref = ray.put(obj, _owner=cache_actor)
    # pass obj_ref wrapped in list to avoid de-referencing
    ray.get(cache_actor.cache_obj_ref.remote([obj_ref], context))
    print('Cached obj')


@ray.remote(num_cpus=0.001)
def load_if_needed(
    context: Dict[str, Any],
    data_store_adapter: DataStoreAdapter,
    path: str,
    is_feature: bool = False,
) -> Block:
    s = 'feature' if is_feature else 'data'
    df, should_cache = _get_from_cache(context)
    if df is not None:
        print(f'[Cached] Loading {s} block started')
        return df
    print(f'Loading {s} block started')
    t = time.time()
    df = data_store_adapter.load_df(path)
    if not is_ts_sorted(df):
        raise ValueError('[Data] df is not ts sorted')
    if should_cache:
        _cache(df, context)
    print(f'Loading {s} block finished {time.time() - t}s')
    return df


@ray.remote(num_cpus=0.9)
def preprocess_data_block(
    block: Block,
    data_def: Type[DataSourceDefinition]
) -> Block:
    # TODO similar caching to load_if_needed ?
    t = time.time()
    res = data_def.preprocess(block)
    print(f'[{data_def}] Preprocessing data block finished {time.time() - t}s')
    return res


@ray.remote(num_cpus=0.001)
def load_and_preprocess(
    context: Dict[str, Any],
    path: str,
    data_def: Type[DataSourceDefinition],
    data_store_adapter: DataStoreAdapter,
    is_feature: bool = False,
) -> Block:
    block = ray.get(load_if_needed.remote(context=context, data_store_adapter=data_store_adapter, path=path, is_feature=is_feature))
    preproc_block = ray.get(preprocess_data_block.remote(block=block, data_def=data_def))
    return preproc_block


@ray.remote(num_cpus=0.9)
def gen_synth_events(
    context: Dict[str, Any],
    interval: Interval,
    synth_data_def: Type[SyntheticDataSourceDefinition],
    params: Dict,
) -> Block:
    return synth_data_def.gen_synthetic_events(interval=interval, params=params)

# TODO for Virtual clock
# https://stackoverflow.com/questions/53829383/mocking-the-internal-clock-of-asyncio-event-loop
# aiotools Virtual Clock
# https://gist.github.com/damonjw/35aac361ca5d313ee9bf79e00261f4ea
# https://simpy.readthedocs.io/en/latest/
# https://github.com/salabim/salabim
# https://github.com/KlausPopp/Moddy
# https://towardsdatascience.com/object-oriented-discrete-event-simulation-with-simpy-53ad82f5f6e2
# https://towardsdatascience.com/simulating-real-life-events-in-python-with-simpy-619ffcdbf81f
# https://github.com/KarrLab/de_sim
# https://github.com/FuchsTom/ProdSim
# https://github.com/topics/discrete-event-simulation?l=python&o=desc&s=forks
# https://docs.python.org/3/library/tkinter.html
# TODO this should be in Feature class ?
@ray.remote(num_cpus=0.9)
def calculate_feature(
    context: Dict[str, Any],
    feature: Feature,
    dep_refs: Dict[Feature, List[ObjectRef[Block]]],
    interval: Interval,
    data_store_adapter: DataStoreAdapter,
    store: bool
) -> Block:
    df, should_cache = _get_from_cache(context)
    if df is not None:
        print(f'[{feature}][Cached] Calc feature finished')
        return df
    print(f'[{feature}] Calc feature block started')
    # TODO add mem tracking
    # this loads blocks for all dep features from shared object store to workers heap
    # hence we need to reserve a lot of mem here
    dep_features = list(dep_refs.keys())
    dep_block_refs = list(dep_refs.values())
    all_block_refs = list(itertools.chain(dep_block_refs))
    all_objs = ray.get(*all_block_refs)
    start = 0
    deps = {}
    for i in range(len(dep_features)):
        dep_feature = dep_features[i]
        dep_blocks = all_objs[start: start + len(dep_block_refs[i])]
        deps[dep_feature] = dep_blocks
        start = start + len(dep_block_refs[i])
    t = time.time()
    merged = merge_blocks(deps)
    print(f'[{feature}] Merged in {time.time() - t}s')

    # TODO use construct_stream_tree in Feature class
    # construct upstreams
    upstreams = {dep_feature: Stream() for dep_feature in deps.keys()}

    # TODO unify feature_definition.stream return type
    s = feature.data_definition.stream(upstreams, feature.params)
    if isinstance(s, Tuple):
        out_stream = s[0]
        state = s[1]
    else:
        out_stream = s

    t = time.time()
    df = run_named_events_stream(merged, upstreams, out_stream, interval)

    # TODO add proper column naming here

    print(f'[{feature}] Events run in {time.time() - t}s')

    if not is_ts_sorted(df):
        raise ValueError('[Feature] df is not ts sorted')
    if should_cache:
        _cache(df, context)
    print(f'[{feature}] Calc feature block finished {time.time() - t}s')
    if store:
        # TODO make a separate actor pool for S3 IO and batchify store operation
        t = time.time()
        db_actor = get_db_actor()
        catalog_item = catalog_feature_block(feature, df, interval, data_store_adapter)
        exists = ray.get(db_actor.in_feature_catalog.remote(catalog_item))
        if not exists:
            # TODO this will block, we need to asyncify, using IO actor pool mentioned above?
            data_store_adapter.store_df(catalog_item.path, df)
            write_res = ray.get(db_actor.write_batch.remote([catalog_item]))
            print(f'[{feature}] Store feature block finished {time.time() - t}s')
        else:
            print(f'[{feature}] Feature block already stored')

    return df


# TODO set memory consumption
# TODO move to tasks?
@ray.remote
def point_in_time_join_block(
    interval: Interval,
    blocks_refs_per_feature: Dict[Feature, ObjectRef[Block]],
    prev_block_ref_per_feature: Dict[Feature, ObjectRef[Block]],
    label_feature: Optional[Feature],
    result_owner: Optional[ray.actor.ActorHandle] = None
) -> ObjectRef[pd.DataFrame]: # TODO is it the same as pd.DataFrame

    # TODO this loads all dfs at once,
    # TODO can we do it iteratively so gc has time to collect old dfs to reduce mem footprint? (tradeoff speed/memory)
    print('Join started')
    concated = {}
    for feature in blocks_refs_per_feature:
        block_refs = [prev_block_ref_per_feature[feature]] if feature in prev_block_ref_per_feature else []
        block_refs.append(blocks_refs_per_feature[feature])

        # TODO have single ray.get
        blocks = ray.get(block_refs)
        concated[feature] = concat(blocks)

    if label_feature is not None:
        dfs = [concated[label_feature]] # make sure label is first so that we can use it's ts as join keys
    else:
        dfs = []

    # make result blocks and features same order
    for feature in concated:
        if label_feature is not None and feature == label_feature:
            # it's already there
            continue
        dfs.append(concated[feature])

    t = time.time()
    merged = merge_asof_multi(dfs)

    print(f'Join finished, merged {len(dfs)} blocks in {time.time() - t}s')
    res = sub_df_ts(merged, interval.lower, interval.upper)
    # return res
    if result_owner is not None:
        ref = ray.put(res, _owner=result_owner)
    else:
        ref = ray.put(res)
    return ref


@ray.remote
def lookahead_shift_blocks(block_refs: List[ObjectRef[Block]], interval: Interval, lookahead: str):
    print('Lookahead shift block started')
    blocks = ray.get(block_refs)
    concated = concat(blocks)
    shifted_concated = lookahead_shift(concated, lookahead)
    shifted = sub_df_ts(shifted_concated, interval.lower, interval.upper)
    # add label_ prefix
    cols = list(shifted.columns)
    cols.remove('timestamp')
    if 'receipt_timestamp' in cols:
        cols.remove('receipt_timestamp')
    cols_new = [f'label_{c}' for c in cols]
    shifted = shifted.rename(columns=dict(zip(cols, cols_new)))

    print('Lookahead shift block finished')
    return shifted


def catalog_feature_block(feature: Feature, df: pd.DataFrame, interval: Interval, data_store_adapter: DataStoreAdapter) -> FeatureCatalog:
    _time_range = df_utils.time_range(df)

    # TODO day_str
    date_str = datetime.fromtimestamp(_time_range[1], tz=pytz.utc).strftime('%Y-%m-%d')
    # check if end_ts is also same date:
    date_str_end = datetime.fromtimestamp(_time_range[2], tz=pytz.utc).strftime('%Y-%m-%d')
    if date_str != date_str_end:
        raise ValueError(f'start_ts and end_ts belong to different dates: {date_str}, {date_str_end}')

    catalog_item_params = {}

    # TODO window, sampling, feature_params, data_params, tags
    catalog_item_params.update({
        FeatureCatalog.owner_id.name: '0',
        FeatureCatalog.feature_def.name: feature.data_definition.__name__,
        FeatureCatalog.key.name: feature.key,
        # TODO pass interval directly instead of start, end? or keep both?
        FeatureCatalog.start_ts.name: interval.lower,
        FeatureCatalog.end_ts.name: interval.upper,
        # FeatureCatalog.start_ts.name: _time_range[1],
        # FeatureCatalog.end_ts.name: _time_range[2],
        FeatureCatalog.size_in_memory_kb.name: df_utils.get_size_kb(df),
        FeatureCatalog.num_rows.name: df_utils.get_num_rows(df),
        FeatureCatalog.date.name: date_str,
    })
    df_hash = df_utils.hash_df(df)
    catalog_item_params[FeatureCatalog.hash.name] = df_hash

    res = FeatureCatalog(**catalog_item_params)
    if res.path is None:
        res.path = data_store_adapter.make_feature_catalog_block_path(res)
    return res
