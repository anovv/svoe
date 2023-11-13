from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Type

import ciso8601
import streamz
from intervaltree import Interval

from common.time.utils import split_time_range_between_ts, ts_to_str_date
from featurizer.blocks.blocks import BlockRangeMeta, BlockRange, ranges_to_interval_dict, get_overlaps, \
    prune_overlaps, meta_to_interval

from featurizer.feature_stream.feature_stream_graph import FeatureStreamGraph, NamedDataEvent, GroupedNamedDataEvent
from featurizer.task_graph.tasks import merge_blocks
from featurizer.config import FeaturizerConfig
from featurizer.features.feature_tree.feature_tree import Feature, construct_features_from_configs
from featurizer.storage.data_store_adapter.data_store_adapter import DataStoreAdapter
from featurizer.storage.data_store_adapter.local_data_store_adapter import LocalDataStoreAdapter
from featurizer.storage.featurizer_storage import FeaturizerStorage
import featurizer.data_definitions.data_definition as data_def

import concurrent.futures

from backtester.models.instrument import Instrument

# free data https://www.cryptoarchive.com.au/faq
# https://ccdata.io/


@dataclass
class DataStreamEvent:
    timestamp: float
    receipt_timestamp: float
    feature_values: Dict[Feature, Dict[str, float]]


# Provides generator interface for already stored events
class OfflineFeatureStreamGenerator:

    NUM_IO_THREADS = 16

    def __init__(self, featurizer_config: FeaturizerConfig, data_store_adapter: DataStoreAdapter = LocalDataStoreAdapter(), price_sampling_period: str = '1s'):
        self._price_sampling_period = price_sampling_period
        self._data_store_adapter = data_store_adapter
        self.features = construct_features_from_configs(featurizer_config.feature_configs)
        self.cur_out_event: Optional[DataStreamEvent] = None
        self.should_construct_new_out_event = True

        # sink function for unified out stream
        def _unified_out_stream_callback(grouped_event: GroupedNamedDataEvent):
            if grouped_event is None:
                raise ValueError('Stream returned None event')

            for e in grouped_event:
                _feature = e[0]
                event = e[1]

                if self.should_construct_new_out_event:
                    self.cur_out_event = DataStreamEvent(
                        timestamp=event['timestamp'],
                        receipt_timestamp=event['receipt_timestamp'],
                        feature_values={}
                    )
                    self.should_construct_new_out_event = False
                self.cur_out_event.feature_values[_feature] = event

        self.feature_stream_graph = FeatureStreamGraph(self.features, combine_outputs=True, combined_out_callback=_unified_out_stream_callback)

        storage = FeaturizerStorage()
        data_ranges_meta = storage.get_data_sources_meta(self.features, start_date=featurizer_config.start_date, end_date=featurizer_config.end_date)
        # TODO indicate if data ranges are empty
        data_ranges = self.load_data_ranges(data_ranges_meta)

        self.input_data_events: List[NamedDataEvent] = self.merge_data_ranges(data_ranges)
        self.cur_input_event_index = 0

        self._sampled_mid_prices: Dict[Instrument, List[Tuple[float, float]]] = {}
        self._last_sampled_ts = None

    # TODO util this?
    def load_data_ranges(self, ranges_meta_per_data: Dict[Feature, List[BlockRangeMeta]]) -> Dict[Interval, Dict[Feature, BlockRange]]:
        ranges_meta_dict_per_data = {}
        for data in ranges_meta_per_data:
            meta = ranges_meta_per_data[data]
            ranges_meta_dict_per_data[data] = ranges_to_interval_dict(meta)

        range_meta_intervals: Dict[Interval, Dict[Feature, BlockRangeMeta]] = prune_overlaps(get_overlaps(ranges_meta_dict_per_data))

        # count number of blocks
        num_blocks = 0
        for interval in range_meta_intervals:
            for feature in range_meta_intervals[interval]:
                num_blocks += len(range_meta_intervals[interval][feature])

        # init data_ranges with empty lists. They will be populated later
        data_ranges = {}
        for interval in range_meta_intervals:
            for feature in range_meta_intervals[interval]:
                if interval not in data_ranges:
                    data_ranges[interval] = {}
                data_ranges[interval][feature] = [None] * len(range_meta_intervals[interval][feature])

        executor_futures = {}

        def _load_and_store_block(cur_block_id: int, path: str):
            print(f'Started loading block {cur_block_id}/{num_blocks}')
            df = self._data_store_adapter.load_df(path)
            print(f'Finished loading block {cur_block_id}/{num_blocks}')
            return df

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.NUM_IO_THREADS) as executor:
            block_id = 1
            for interval in range_meta_intervals:
                for feature in range_meta_intervals[interval]:
                    for block_position in range(len(range_meta_intervals[interval][feature])):
                        block_meta = range_meta_intervals[interval][feature][block_position]
                        if feature.data_definition.is_synthetic():
                            data_ranges[interval][feature][block_position] = feature.data_definition.gen_synthetic_events(
                                interval=meta_to_interval(block_meta),
                                params=feature.params
                            )
                        else:
                            path = block_meta['path']
                            key = (interval, feature, block_position)
                            executor_futures[key] = executor.submit(_load_and_store_block, cur_block_id=block_id, path=path)
                            block_id += 1

        for key in executor_futures:
            executor_future = executor_futures[key]
            interval, feature, block_position = key
            block = executor_future.result()

            # data_ranges dict already constructed above
            # TODO preproc only if needed
            preproc_block = feature.data_definition.preprocess(block)
            data_ranges[interval][feature][block_position] = preproc_block

        return data_ranges

    def merge_data_ranges(self, data_ranges: Dict[Interval, Dict[Feature, BlockRange]]) -> List[NamedDataEvent]:
        # return {i: merge_blocks(b) for (i, b) in data_ranges}
        merged_per_data: Dict[Interval, List[NamedDataEvent]] = {}
        for interval in data_ranges:
            merged_per_data[interval] = merge_blocks(data_ranges[interval])

        res = []
        sorted_intervals = sorted(merged_per_data.keys())
        for interval in sorted_intervals:
            res.extend(merged_per_data[interval])
        return res

    def _pop_input_events(self) -> GroupedNamedDataEvent:
        res = []
        data, input_event = self.input_data_events[self.cur_input_event_index]
        timestamp = input_event['timestamp']
        res.append((data, input_event))
        self.cur_input_event_index += 1

        # group events with same ts
        while self.cur_input_event_index < len(self.input_data_events):
            next_data, next_input_event = self.input_data_events[self.cur_input_event_index]
            # TODO float comparison
            if timestamp == next_input_event['timestamp']:
                res.append((next_data, next_input_event))
                self.cur_input_event_index += 1
            else:
                break

        return tuple[res]

    def next(self) -> DataStreamEvent:
        grouped_input_events = self._pop_input_events()
        for named_data_event in grouped_input_events:
            self.feature_stream_graph.emit_named_data_event(named_data_event)

        self.should_construct_new_out_event = True

        # update sampled mid prices
        if self.cur_out_event is not None:
            cur_ts = self.cur_out_event.timestamp
            if self._last_sampled_ts is None or cur_ts - self._last_sampled_ts > self._price_sampling_period:
                mid_prices = self.get_cur_mid_prices()
                for instrument in mid_prices:
                    if instrument in self._sampled_mid_prices:
                        self._sampled_mid_prices[instrument].append((cur_ts, mid_prices[instrument]))
                    else:
                        self._sampled_mid_prices[instrument] = [(cur_ts, mid_prices[instrument])]
        return self.cur_out_event

    def has_next(self) -> bool:
        return self.cur_input_event_index < len(self.input_data_events)

    def get_cur_mid_prices(self) -> Dict[Instrument, float]:
        return OfflineFeatureStreamGenerator.get_mid_prices_from_event(self.cur_out_event)

    def get_sampled_mid_prices(self) -> Dict[Instrument, List[Tuple[float, float]]]:
        return self._sampled_mid_prices

    @classmethod
    def get_mid_prices_from_event(cls, data_event: DataStreamEvent) -> Dict[Instrument, float]:
        mid_prices = {}

        for feature in data_event.feature_values:
            mid_price = None
            for col in data_event.feature_values[feature]:
                if col == 'mid_price':
                    mid_price = data_event.feature_values[feature][col]
                    instrument = OfflineFeatureStreamGenerator.get_instrument_for_feature(feature)
                    mid_prices[instrument] = mid_price
                    break
            if mid_price is None:
                raise ValueError('DataGenerator event should contain mid_price field for all data/instrument inputs')

        return mid_prices

    @classmethod
    def get_instrument_for_feature(cls, feature):
        data_deps = feature.get_data_sources()
        if len(data_deps) != 1:
            raise ValueError('Expected exactly 1 data source dependency')
        params = data_deps[0].params

        # TODO make model for params?
        instr = Instrument(
            params['exchange'],
            params['instrument_type'],
            params['symbol'],
        )
        return instr

    @classmethod
    def get_feature_for_instrument(cls, data_event: DataStreamEvent, instrument: Instrument, feature_definition: Optional[Type[data_def.DataDefinition]] = None) -> Optional[Feature]:
        # TODO cache this to avoid recalculation on each update? or make a FeatureStreamSchema abstraction?
        _feature = None
        for feature in data_event.feature_values:
            if feature_definition is not None and feature.data_definition != feature_definition:
                continue
            instr = cls.get_instrument_for_feature(feature)
            if instr == instrument:
                if _feature is not None:
                    raise ValueError(f'Found more then one feature for instrument {instrument}, event: {data_event}')
                _feature = feature

        return _feature

    @classmethod
    def split(cls, featurizer_config: FeaturizerConfig, num_splits: int) -> List['OfflineFeatureStreamGenerator']:
        start_date = featurizer_config.start_date
        end_date = featurizer_config.end_date
        generators = []
        start_ts = ciso8601.parse_datetime(start_date).timestamp()
        end_ts = ciso8601.parse_datetime(end_date).timestamp()
        splits = split_time_range_between_ts(start_ts, end_ts, num_splits, 0.1)
        date_range_splits = [(ts_to_str_date(i.lower), ts_to_str_date(i.upper)) for i in splits]

        for _start_date, _end_date in date_range_splits:
            config_split = featurizer_config.copy(deep=True)
            config_split.start_date = _start_date
            config_split.end_date = _end_date
            gen = OfflineFeatureStreamGenerator(config_split)
            # TODO check if generator is empty
            generators.append(gen)

        return generators
