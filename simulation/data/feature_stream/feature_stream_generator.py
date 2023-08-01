from typing import Dict, List, Tuple, Any

from intervaltree import Interval

from featurizer.blocks.blocks import BlockRangeMeta, Block, BlockRange, ranges_to_interval_dict, get_overlaps, \
    prune_overlaps
from featurizer.calculator.tasks import merge_blocks
from featurizer.config import FeaturizerConfig
from featurizer.features.feature_tree.feature_tree import construct_feature_tree, Feature, construct_stream_tree
from featurizer.storage.featurizer_storage import FeaturizerStorage, data_key
import featurizer.data_definitions.data_definition as f

import concurrent.futures

from simulation.data.data_generator import DataGenerator
from simulation.models.instrument import Instrument
from utils.common_utils import flatten_tuples
from utils.pandas.df_utils import load_df


class FeatureStreamGenerator(DataGenerator):

    NUM_IO_THREADS = 16

    def __init__(self, featurizer_config: FeaturizerConfig):
        # TODO this logic is duplicated in featurizer/runner.py, util it?
        self.features = []
        for feature_config in featurizer_config.feature_configs:
            self.features.append(construct_feature_tree(
                feature_config.feature_definition,
                feature_config.data_params,
                feature_config.feature_params
            ))

        # build data streams trees
        self.data_streams_per_feature = {}
        for f in self.features:
            out, data_streams = construct_stream_tree(f)
            self.data_streams_per_feature[f] = out, data_streams

        # constructed unified out stream
        first_feature = self.features[0]
        first_out_stream, _ = self.data_streams_per_feature[first_feature]
        unified_out_stream = first_out_stream.map(lambda e: [first_feature, e])
        for i in range(1, len(self.features)):
            feature = self.features[i]
            out_stream, _ = self.data_streams_per_feature[feature]
            out_stream = out_stream.map(lambda e: [feature, e])
            unified_out_stream = unified_out_stream.combine_latest(out_stream)

        self.unified_out_stream = unified_out_stream
        self.cur_out_event = None
        self.should_construct_new_out_event = True

        # sink function for unified out stream
        def _unified_out_stream(elems: Tuple):
            if elems is None:
                raise ValueError('Stream returned None event')
            elems = flatten_tuples(elems)
            # (
            #   [feature-MidPriceFD-0-4f83d18e, frozendict.frozendict(
            #       {'timestamp': 1675216068.340869,
            #       'receipt_timestamp': 1675216068.340869,
            #       'mid_price': 23169.260000000002})],
            #   [feature-VolatilityStddevFD-0-ad30ace5, frozendict.frozendict(
            #       {'timestamp': 1675216068.340869,
            #       'receipt_timestamp': 1675216068.340869,
            #       'volatility': 0.00023437500931322575})]
            #  )
            for l in elems:
                feature = l[0]
                event = l[1]
                interval = list(self.input_data_events.keys())[self.cur_interval_id]
                if interval.lower > event['timestamp'] or event['timestamp'] > interval.upper:
                    # skip if event is outside of current interval
                    return

                if self.should_construct_new_out_event:
                    self.cur_out_event = {}
                    self.should_construct_new_out_event = False
                self.cur_out_event[feature] = event

        self.unified_out_stream.sink(_unified_out_stream)

        storage = FeaturizerStorage()
        data_deps = set()
        for feature in self.features:
            for d in feature.get_data_deps():
                data_deps.add(d)

        # TODO infer Instrument objects from this
        data_keys = [data_key(d.params) for d in data_deps]
        ranges_meta_per_data_key = storage.get_data_meta(data_keys, start_date=featurizer_config.start_date,
                                                         end_date=featurizer_config.end_date)
        ranges_meta_per_data = {data: ranges_meta_per_data_key[data_key(data.params)] for data in data_deps} # Dict[Feature, List[BlockRangeMeta]]
        data_ranges = self.load_data_ranges(ranges_meta_per_data)
        self.input_data_events = self.merge_data_ranges(data_ranges)
        self.cur_interval_id = 0
        self.cur_input_event_index = 0


    # TODO util this?
    def load_data_ranges(self, ranges_meta_per_data: Dict[Feature, List[BlockRangeMeta]]) -> Dict[Interval, Dict[Feature, BlockRange]]:
        ranges_meta_dict_per_data = {}
        for data in ranges_meta_per_data:
            meta = ranges_meta_per_data[data]
            ranges_meta_dict_per_data[data] = ranges_to_interval_dict(meta)

        range_meta_intervals = prune_overlaps(get_overlaps(ranges_meta_dict_per_data)) # Dict[Interval, Dict[Feature, BlockRangeMeta]]

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
            df = load_df(path)
            print(f'Finished loading block {cur_block_id}/{num_blocks}')
            return df

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.NUM_IO_THREADS) as executor:
            block_id = 1
            for interval in range_meta_intervals:
                for feature in range_meta_intervals[interval]:
                    for block_position in range(len(range_meta_intervals[interval][feature])):
                        block_meta = range_meta_intervals[interval][feature][block_position]
                        path = block_meta['path']
                        key = (interval, feature, block_position)
                        executor_futures[key] = executor.submit(_load_and_store_block, cur_block_id=block_id, path=path)
                        block_id += 1

        for key in executor_futures:
            executor_future = executor_futures[key]
            interval, feature, block_position = key
            block = executor_future.result()

            # data_ranges dict already constructed above
            data_ranges[interval][feature][block_position] = block

        return data_ranges

    def merge_data_ranges(self, data_ranges: Dict[Interval, Dict[Feature, BlockRange]]) -> Dict[Interval, List[Tuple[Feature, f.Event]]]:
        # return {i: merge_blocks(b) for (i, b) in data_ranges}
        res = {}
        for interval in data_ranges:
            res[interval] = merge_blocks(data_ranges[interval])
        return res

    def _pop_input_events(self) -> List[Tuple[Feature, f.Event]]:
        # move interval if necessary
        if self.cur_interval_id >= len(self.input_data_events.keys()):
            raise ValueError('DataGenerator out of bounds')
        interval = list(self.input_data_events.keys())[self.cur_interval_id]
        input_events = self.input_data_events[interval]
        if self.cur_input_event_index >= len(input_events):
            self.cur_interval_id += 1
            if self.cur_interval_id >= len(self.input_data_events.keys()):
                raise ValueError('DataGenerator out of bounds')
            self.cur_input_event_index = 0
            interval = list(self.input_data_events.keys())[self.cur_interval_id]
            input_events = self.input_data_events[interval]

        res = []
        data, input_event = input_events[self.cur_input_event_index]
        timestamp = input_event['timestamp']
        res.append((data, input_event))
        self.cur_input_event_index += 1

        # group events with same ts
        while self.cur_input_event_index < len(input_events):
            next_data, next_input_event = input_events[self.cur_input_event_index]
            # TODO float comparison
            if timestamp == next_input_event['timestamp']:
                res.append((next_data, next_input_event))
                self.cur_input_event_index += 1
            else:
                break

        return res

    # TODO typing
    def next(self) -> Dict:
        grouped_input_events = self._pop_input_events()
        for (data, input_event) in grouped_input_events:
            for feature in self.data_streams_per_feature:
                _, data_streams = self.data_streams_per_feature[feature]
                if data in data_streams:
                    data_streams[data].emit(input_event)

        self.should_construct_new_out_event = True
        return self.cur_out_event

    def has_next(self) -> bool:
        if self.cur_interval_id >= len(self.input_data_events.keys()):
            return False

        # last elem
        if self.cur_interval_id == len(self.input_data_events.keys()) - 1:
            interval = list(self.input_data_events.keys())[self.cur_interval_id]
            input_events = self.input_data_events[interval]
            if self.cur_input_event_index == len(input_events) - 1:
                return False

        return True

    def get_cur_mid_prices(self) -> Dict[Instrument, float]:
        # TODO this is hacky, we need to map feature (really data in this case) to instrument properly
        mid_price = None
        for feature in self.cur_out_event:
            for key in self.cur_out_event[feature]:
                if key == 'mid_price':
                    mid_price = self.cur_out_event[feature][key]
                    break
        if mid_price is None:
            raise ValueError('DataGenerator should provide mid_price stream for all data/instrument inputs')
        return {Instrument('BINANCE', 'spot', 'BTC-USDT'): mid_price}
