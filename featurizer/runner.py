from typing import Optional

import pandas as pd

from common.pandas.df_utils import concat, downsample_uniform
from featurizer.actors.cache_actor import get_cache_actor, create_cache_actor
from featurizer.calculator.calculator import build_feature_label_set_task_graph
from featurizer.calculator.executor import execute_graph
from featurizer.storage.featurizer_storage import FeaturizerStorage, data_key
from featurizer.config import FeaturizerConfig
from featurizer.features.feature_tree.feature_tree import construct_feature_tree

import ray.experimental

import ray

# TODO these are local packages to pass to dev cluster
import featurizer
import common
import client

LOCAL_PACKAGES_TO_PASS_TO_REMOTE_DEV_RAY_CLUSTER = [featurizer, common, client]


class Featurizer:

    @classmethod
    def run(cls, config: FeaturizerConfig, ray_address: str, parallelism: int):
        features = []
        for feature_config in config.feature_configs:
            features.append(construct_feature_tree(
                feature_config.feature_definition,
                feature_config.data_params,
                feature_config.feature_params
            ))

        storage = FeaturizerStorage()
        data_deps = set()
        for feature in features:
            for d in feature.get_data_deps():
                data_deps.add(d)
        data_keys = [data_key(d.params) for d in data_deps]
        ranges_meta_per_data_key = storage.get_data_meta(data_keys, start_date=config.start_date, end_date=config.end_date)
        data_ranges_meta = {data: ranges_meta_per_data_key[data_key(data.params)] for data in data_deps}

        stored_features_meta = storage.get_features_meta(features, start_date=config.start_date, end_date=config.end_date)

        label_feature = features[config.label_feature_index]

        cache = {}
        features_to_store = [features[i] for i in config.features_to_store]

        with ray.init(address=ray_address, ignore_reinit_error=True, runtime_env={
            'py_modules': LOCAL_PACKAGES_TO_PASS_TO_REMOTE_DEV_RAY_CLUSTER,
            'pip': ['pyhumps']
        }):
            # remove old actor from prev session if it exists
            try:
                cache_actor = get_cache_actor()
                ray.kill(cache_actor)
            except ValueError:
                pass

            cache_actor = create_cache_actor(cache)
            # TODO pass params indicating if user doesn't want to join/lookahead and build/execute graph accordingly
            dag = build_feature_label_set_task_graph(
                features=features,
                label=label_feature,
                label_lookahead=config.label_lookahead,
                data_ranges_meta=data_ranges_meta,
                obj_ref_cache=cache,
                features_to_store=features_to_store,
                stored_feature_blocks_meta=stored_features_meta,
                result_owner=cache_actor
            )

            # TODO first two values are weird outliers for some reason, why?
            # df = df.tail(-2)
            refs = execute_graph(dag=dag, parallelism=parallelism)
            ray.get(cache_actor.record_featurizer_result_refs.remote(refs))

    # TODO
    @classmethod
    def get_metadata(cls) -> pd.DataFrame:
        # should return metadata about featurization result e.g. in memory size, num blocks, schema, set name, etc.
        raise NotImplementedError

    @classmethod
    def get_data(cls, start: Optional[str] = None, end: Optional[str] = None, pick_every_nth_row: Optional[int] = 1) -> pd.DataFrame:
        cache_actor = get_cache_actor()
        refs = ray.get(cache_actor.get_featurizer_result_refs.remote())

        # TODO filter refs based on start/end
        @ray.remote
        def downsample(df: pd.DataFrame, nth_row: int) -> pd.DataFrame:
            return downsample_uniform(df, nth_row)

        if pick_every_nth_row != 1:
            # TODO const num_cpus ?
            downsampled_refs = [downsample.remote(ref, pick_every_nth_row).options(num_cpus=0.9) for ref in refs]
        else:
            downsampled_refs = refs

        downsampled_dfs = ray.get(downsampled_refs)
        return concat(downsampled_dfs)


if __name__ == '__main__':
    ray_address = 'ray://127.0.0.1:10001'
    with ray.init(address=ray_address, ignore_reinit_error=True, runtime_env={
        'py_modules': LOCAL_PACKAGES_TO_PASS_TO_REMOTE_DEV_RAY_CLUSTER,
        'pip': ['pyhumps']
    }):
        df = Featurizer.get_data()
        print(df)