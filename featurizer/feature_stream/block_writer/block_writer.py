from typing import List, Any, Dict, Optional, Type

import pandas as pd

from featurizer.data_definitions.data_definition import Event, DataDefinition
from featurizer.data_ingest.pipelines.cryptotick.tasks import make_data_source_block_metadata
from featurizer.feature_stream.block_writer.compactor import Compactor
from featurizer.features.feature_tree.feature_tree import Feature
from featurizer.storage.data_store_adapter.data_store_adapter import DataStoreAdapter
from featurizer.storage.data_store_adapter.local_data_store_adapter import LocalDataStoreAdapter
from featurizer.task_graph.tasks import make_feature_block_metadata


class BlockWriter:

    def __init__(
        self,
        default_compactor: Compactor,
        compactors: Optional[Dict[Type[DataDefinition], Compactor]] = None,
        data_store_adapter: DataStoreAdapter = LocalDataStoreAdapter(),
    ):
        self._events_to_store: Dict[Feature, List[Event]] = {}
        self._default_compactor = default_compactor
        self._data_store_adapter = data_store_adapter
        self._compactors = compactors
        self._is_running = False

    def start(self):
        pass

    def store_loop(self):
        while self._is_running:
            for feature in self._events_to_store:
                compactor = self._default_compactor
                if self._compactors is not None and feature.data_definition in self._compactors:
                    compactor = self._compactors[feature.data_definition]

                # TODO if it is l2_book snap, pass extra args in kwargs
                df = compactor.compact(feature, self._events_to_store[feature])
                if df is None:
                    continue

    def _store_block(self, df: pd.DataFrame, feature: Feature):
        if feature.data_definition.is_data_source():
            metadata_item = make_data_source_block_metadata(df, {}, self._data_store_adapter)
        else:
            interval = None # TODO get from df
            metadata_item = make_feature_block_metadata(feature, df, interval, self._data_store_adapter)

        # TODO write SQL db, write block storage
        # TODO retries



