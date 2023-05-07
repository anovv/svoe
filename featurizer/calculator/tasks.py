import heapq
import itertools
import time
from typing import Dict, List, Tuple

import ray
from portion import Interval
from ray.types import ObjectRef
from streamz import Stream

from featurizer.blocks.blocks import Block, BlockMeta, BlockRange
from featurizer.data_definitions.data_definition import Event
from featurizer.features.feature_tree.feature_tree import Feature
from utils.streamz.stream_utils import run_named_events_stream
from utils.pandas.df_utils import load_df

@ray.remote(num_cpus=0.001)
def load_if_needed(
    block_meta: BlockMeta,
) -> Block:
    # TODO if using Ray's Plasma, check shared obj store first, if empty - load from s3
    # TODO figure out how to split BlockRange -> Block and cache if needed
    # TODO sync keys
    print('Load started')
    t = time.time()
    path = block_meta['path']
    df = load_df(path)
    print(f'Load finished {time.time() - t}s')
    return df

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
    feature: Feature,
    dep_refs: Dict[Feature, List[ObjectRef[Block]]], # maps dep feature to BlockRange # TODO List[BlockRange] when using 'holes'
    interval: Interval
) -> Block:
    print('Calc feature started')
    t = time.time()
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

    merged = merge_blocks(deps)
    # construct upstreams
    upstreams = {dep_named_feature: Stream() for dep_named_feature in deps.keys()}
    s = feature.feature_definition.stream(upstreams, feature.params)
    if isinstance(s, Tuple):
        out_stream = s[0]
        state = s[1]
    else:
        out_stream = s

    df = run_named_events_stream(merged, upstreams, out_stream, interval)
    print(f'Calc feature finished {time.time() - t}s')
    return df


# TODO util this
# TODO we assume no 'holes' here
# TODO can we use pandas merge_asof here or some other merge functionality?
def merge_blocks(
    blocks: Dict[Feature, BlockRange]
) -> List[Tuple[Feature, Event]]:
    merged = None
    features = list(blocks.keys())
    for i in range(0, len(features)):
        feature = features[i]
        block_range = blocks[feature]
        named_events = []
        for block in block_range:
            parsed = feature.feature_definition.parse_events(block)
            named = []
            for e in parsed:
                named.append((feature, e))
            named_events = list(heapq.merge(named_events, named, key=lambda named_event: named_event[1]['timestamp']))

        if i == 0:
            merged = named_events
        else:
            # TODO explore heapdict
            merged = list(heapq.merge(merged, named_events, key=lambda named_event: named_event[1]['timestamp']))

    return merged


@ray.remote(num_cpus=0.001)
def store_day(feature: Feature, refs: List[ObjectRef[Block]], day: str) -> Dict:
    # TODO
    return {}
