from typing import List

from ray.types import ObjectRef

from featurizer.actors.cache_actor import get_cache_actor, create_cache_actor
from featurizer.calculator.calculator import build_feature_set_task_graph, point_in_time_join_dag, \
    build_feature_label_set_task_graph
from featurizer.calculator.executor import execute_graph
from featurizer.storage.featurizer_storage import FeaturizerStorage, data_key
from featurizer.config import FeaturizerConfig
from featurizer.features.feature_tree.feature_tree import construct_feature_tree

import ray


class Featurizer:

    @classmethod
    def run(cls, config_path: str):
        config = FeaturizerConfig.load_config(path=config_path)
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

        # TODO pass params indicating if user doesn't want to join/lookahead and build/execute graph accordingly

        dag = build_feature_label_set_task_graph(
            features=features,
            label=label_feature,
            label_lookahead=config.label_lookahead,
            data_ranges_meta=data_ranges_meta,
            obj_ref_cache=cache,
            features_to_store=features_to_store,
            stored_feature_blocks_meta=stored_features_meta
        )

        # TODO pass cluster address in config?
        with ray.init(address='auto', ignore_reinit_error=True):
            # ray.init(address='auto', ignore_reinit_error=True)

            # remove old actor from prev session if it exists
            try:
                cache_actor = get_cache_actor()
                ray.kill(cache_actor)
            except ValueError:
                pass

            cache_actor = create_cache_actor(cache)
            refs = execute_graph(dag)
            ray.get(cache_actor.record_featurizer_result_refs.remote(refs))