import calculator as C
from featurizer.features.data.l2_book_delats.l2_book_deltas import L2BookDeltasData
from featurizer.features.definitions.l2_book_snapshot.l2_book_snapshot_feature_definition import L2BookSnapshotFeatureDefinition
from featurizer.features.definitions.mid_price.mid_price_feature_definition import MidPriceFeatureDefinition
from featurizer.features.blocks.utils import identity_grouping
import portion as P
import unittest
import dask


class TestFeatureCalculator(unittest.TestCase):

    def test_get_ranges_overlaps(self):
        grouped_range = {}
        ranges_a = P.IntervalDict()
        ranges_a[P.closed(1, 4)] = [self.meta(1, 2), self.meta(2.1, 5)]
        ranges_a[P.closed(4.1, 8)] = [self.meta(5, 5.5), self.meta(6, 7)]
        ranges_a[P.closed(9, 15)] = [self.meta(9, 15)]
        grouped_range['feature_a'] = ranges_a

        ranges_b = P.IntervalDict()
        ranges_b[P.closed(2, 5)] = [self.meta(2, 3), self.meta(3.1, 6)]
        ranges_b[P.closed(6, 7)] = [self.meta(6, 7)]
        ranges_b[P.closed(9, 20)] = [self.meta(9, 15), self.meta(15.1, 18), self.meta(18.1, 22)]
        grouped_range['feature_b'] = ranges_b

        expected = P.IntervalDict()
        expected[P.closed(2, 4)] = {
            'feature_a': [{'start_ts': 1, 'end_ts': 2}, {'start_ts': 2.1, 'end_ts': 5}],
            'feature_b': [{'start_ts': 2, 'end_ts': 3}, {'start_ts': 3.1, 'end_ts': 6}]
        }
        expected[P.closed(4.1, 5)] = {
            'feature_a': [{'start_ts': 5, 'end_ts': 5.5}, {'start_ts': 6, 'end_ts': 7}],
            'feature_b': [{'start_ts': 2, 'end_ts': 3}, {'start_ts': 3.1, 'end_ts': 6}]
        }
        expected[P.closed(6, 7)] = {
            'feature_a': [{'start_ts': 5, 'end_ts': 5.5}, {'start_ts': 6, 'end_ts': 7}],
            'feature_b': [{'start_ts': 6, 'end_ts': 7}]
        }
        expected[P.closed(9, 15)] = {
            'feature_a': [{'start_ts': 9, 'end_ts': 15}],
            'feature_b': [{'start_ts': 9, 'end_ts': 15}, {'start_ts': 15.1, 'end_ts': 18},
                          {'start_ts': 18.1, 'end_ts': 22}]
        }

        overlaps = C.get_ranges_overlaps(grouped_range)
        self.assertEqual(overlaps, expected)

    def meta(self, start_ts, end_ts, extra=None):
        # TODO make mock function
        res = {'start_ts': start_ts, 'end_ts': end_ts}
        if extra:
            res.update(extra)
        return res

    # TODO customize dask graph visualization
    # https://stackoverflow.com/questions/58394758/adding-labels-to-a-dask-graph
    # https://stackoverflow.com/questions/67680325/annotations-for-custom-graphs-in-dask
    def test_build_task_graph_l2_snaps(self):
        feature_ranges = self.mock_l2_book_deltas_data_ranges(30 * 1000, 10)
        fd_type = L2BookSnapshotFeatureDefinition
        graph = C.build_task_graph(fd_type, feature_ranges)
        print(graph)
        dask.visualize(*graph)

    def test_build_task_graph_mid_price(self):
        feature_ranges = self.mock_l2_book_deltas_data_ranges(30 * 1000, 10)
        fd_type = MidPriceFeatureDefinition
        graph = C.build_task_graph(fd_type, feature_ranges)
        print(graph)
        dask.visualize(*graph)

    def mock_l2_book_deltas_data_ranges(self, block_len_ms, num_blocks, between_blocks_ms=100, cur_ts=0):
        res = {}
        data_name = f'{L2BookDeltasData.type_str()}-0' # TODO make this Data method
        ranges = []
        for i in range(0, num_blocks):
            meta = self.meta(cur_ts, cur_ts + block_len_ms)
            if i % 2 == 0:
                # TODO sync keys with L2BookSnapshotFeatureDefinition.group_dep_ranges
                meta['snapshot_ts'] = cur_ts + 10 * 1000
                meta['before_snapshot_ts'] = meta['snapshot_ts'] - 1 * 1000
            ranges.append(meta)
            cur_ts += block_len_ms
            cur_ts += between_blocks_ms
        res[data_name] = ranges
        return res


if __name__ == '__main__':
    # unittest.main()
    t = TestFeatureCalculator()
    t.test_build_task_graph_mid_price()
