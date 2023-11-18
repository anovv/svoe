import concurrent.futures
import functools
import time
from threading import Thread
from typing import List, Any, Dict, Optional, Type

import pandas as pd
from portion import Interval

from common.pandas.df_utils import time_range
from featurizer.data_definitions.data_definition import Event, DataDefinition
from featurizer.data_ingest.pipelines.cryptotick.tasks import make_data_source_block_metadata
from featurizer.feature_stream.block_writer.compactor import Compactor
from featurizer.feature_stream.block_writer.memory_based_compactor import MemoryBasedCompactor
from featurizer.features.feature_tree.feature_tree import Feature
from featurizer.sql.client import FeaturizerSqlClient
from featurizer.sql.models.data_source_block_metadata import DataSourceBlockMetadata
from featurizer.sql.models.data_source_metadata import DataSourceMetadata
from featurizer.storage.data_store_adapter.data_store_adapter import DataStoreAdapter
from featurizer.storage.data_store_adapter.local_data_store_adapter import LocalDataStoreAdapter
from featurizer.task_graph.tasks import make_feature_block_metadata

STORE_LOOP_INTERVAL_S = 5

class BlockWriter:

    def __init__(
        self,
        default_compactor: Compactor = MemoryBasedCompactor(),
        compactors: Optional[Dict[Type[DataDefinition], Compactor]] = None,
        data_store_adapter: DataStoreAdapter = LocalDataStoreAdapter(),
    ):
        self._events_to_store: Dict[Feature, List[Event]] = {}
        self._default_compactor = default_compactor
        self._data_store_adapter = data_store_adapter
        self._compactors = compactors

        # TODO decide on if we should use DbActor
        self._sql_client = FeaturizerSqlClient()

        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=128)
        self._loop_thread = Thread(target=self._store_loop)

        self._is_running = False

    def start(self):
        self._is_running = True
        self._loop_thread.start()

    def stop(self):
        self._is_running = False
        self._executor.shutdown(wait=True)
        self._loop_thread.join()

    def append_event(self, feature: Feature, event: Event):
        if feature in self._events_to_store:
            self._events_to_store[feature].append(event)
        else:
            self._events_to_store[feature] = [event]

    def _store_loop(self):
        while self._is_running:
            for feature in self._events_to_store:
                compactor = self._default_compactor
                if self._compactors is not None and feature.data_definition in self._compactors:
                    compactor = self._compactors[feature.data_definition]

                # TODO if it is l2_book snap, pass extra args in kwargs
                dfs = compactor.compact(feature, self._events_to_store[feature])
                if len(dfs) == 0:
                    continue

                for df in dfs:
                    # fire and forget
                    self._executor.submit(functools.partial(self._store_block, self, df, feature))

        # wait for running futures to finish
        self._executor.shutdown(wait=True)

    def _store_block(self, df: pd.DataFrame, feature: Feature):
        if feature.data_definition.is_data_source():
            data_source = feature
            input_item = {
                DataSourceBlockMetadata.key.name: data_source.key,
                DataSourceBlockMetadata.data_source_definition.name: data_source.data_definition.__name__,
                DataSourceMetadata.params.name: data_source.params
            }
            metadata_item = make_data_source_block_metadata(df, input_item, self._data_store_adapter)
        else:
            _time_range = time_range(df)
            interval = Interval(_time_range[0], _time_range[1])
            metadata_item = make_feature_block_metadata(feature, df, interval, self._data_store_adapter)

        # TODO retries
        self._data_store_adapter.store_df(metadata_item.path, df)
        self._sql_client.store_block_metadata_batch([metadata_item])

        # TODO message to log?
        print(f'Stored block for {feature}')
        time.sleep(STORE_LOOP_INTERVAL_S)



