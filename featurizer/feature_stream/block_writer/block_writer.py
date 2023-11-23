import concurrent.futures
import time
from threading import Thread
from typing import List, Dict, Optional, Type

import pandas as pd
from portion import closed

from common.pandas.df_utils import time_range
from featurizer.data_definitions.data_definition import Event, DataDefinition
from featurizer.data_ingest.pipelines.cryptotick.tasks import make_data_source_block_metadata
from featurizer.feature_stream.block_writer.compactor import Compactor
from featurizer.features.feature_tree.feature_tree import Feature
from featurizer.sql.client import FeaturizerSqlClient
from featurizer.sql.models.data_source_block_metadata import DataSourceBlockMetadata
from featurizer.sql.models.data_source_metadata import DataSourceMetadata
from featurizer.sql.models.feature_metadata import FeatureMetadata
from featurizer.storage.data_store_adapter.data_store_adapter import DataStoreAdapter
from featurizer.storage.data_store_adapter.local_data_store_adapter import LocalDataStoreAdapter
from featurizer.task_graph.tasks import make_feature_block_metadata

STORE_LOOP_INTERVAL_S = 5


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

        # TODO decide on if we should use DbActor
        self._sql_client = FeaturizerSqlClient()

        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=128)
        self._loop_thread = Thread(target=self._store_loop, daemon=True)

        self._is_running = False

    def start(self):
        self._is_running = True
        self._loop_thread.start()

    def stop(self):
        self._is_running = False
        self._executor.shutdown(wait=True)
        self._loop_thread.join(timeout=10)

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
                    # self._executor.submit(self._store_block, df, feature)
                    # TODO run in executor after debug
                    self._store_block(df, feature)

            time.sleep(STORE_LOOP_INTERVAL_S)

        # wait for running futures to finish
        self._executor.shutdown(wait=True)

    def _store_block(self, df: pd.DataFrame, feature: Feature):
        print(f'Stored called for {feature}')
        # TODO check if there is an entry in feature/data_source_metadata table
        if feature.data_definition.is_data_source():
            metadata = DataSourceMetadata(
                owner_id='0',  # TODO
                key=feature.key,
                data_source_definition=feature.data_definition.__name__,
                extras={},
                params=feature.params
            )
        else:
            metadata = FeatureMetadata(
                owner_id='0',  # TODO
                key=feature.key,
                feature_definition=feature.data_definition.__name__,
                feature_name=feature.name,
                params=feature.params
            )
        self._sql_client.store_metadata_if_needed([metadata])

        if feature.data_definition.is_data_source():
            data_source = feature
            input_item = {
                DataSourceBlockMetadata.key.name: data_source.key,
                DataSourceBlockMetadata.data_source_definition.name: data_source.data_definition.__name__,
                DataSourceMetadata.params.name: data_source.params
            }
            block_metadata = make_data_source_block_metadata(df, input_item, self._data_store_adapter)
        else:
            _time_range = time_range(df)
            interval = closed(_time_range[1], _time_range[2])
            block_metadata = make_feature_block_metadata(feature, df, interval, self._data_store_adapter)

        # TODO retries
        self._data_store_adapter.store_df(block_metadata.path, df)
        self._sql_client.store_block_metadata_batch([block_metadata])

        # TODO message to log?
        print(f'Stored block for {feature}')



