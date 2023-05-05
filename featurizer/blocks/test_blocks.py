import unittest

import portion as P

from featurizer.blocks.blocks import get_overlaps, mock_meta


class TestBlocks(unittest.TestCase):

    def test_overlaps(self):
        KEY_1 = 'key_1'
        KEY_2 = 'key_2'
        grouped_range = {}
        ranges_a = P.IntervalDict()
        ranges_a[P.closed(1, 4)] = [mock_meta(1, 2), mock_meta(2.1, 5)]
        ranges_a[P.closed(4.1, 8)] = [mock_meta(5, 5.5), mock_meta(6, 7)]
        ranges_a[P.closed(9, 15)] = [mock_meta(9, 15)]
        grouped_range[KEY_1] = ranges_a

        ranges_b = P.IntervalDict()
        ranges_b[P.closed(2, 5)] = [mock_meta(2, 3), mock_meta(3.1, 6)]
        ranges_b[P.closed(6, 7)] = [mock_meta(6, 7)]
        ranges_b[P.closed(9, 20)] = [mock_meta(9, 15), mock_meta(15.1, 18), mock_meta(18.1, 22)]
        grouped_range[KEY_2] = ranges_b

        expected = P.IntervalDict()
        expected[P.closed(2, 4)] = {
            KEY_1: [{'start_ts': 1, 'end_ts': 2}, {'start_ts': 2.1, 'end_ts': 5}],
            KEY_2: [{'start_ts': 2, 'end_ts': 3}, {'start_ts': 3.1, 'end_ts': 6}]
        }
        expected[P.closed(4.1, 5)] = {
            KEY_1: [{'start_ts': 5, 'end_ts': 5.5}, {'start_ts': 6, 'end_ts': 7}],
            KEY_2: [{'start_ts': 2, 'end_ts': 3}, {'start_ts': 3.1, 'end_ts': 6}]
        }
        expected[P.closed(6, 7)] = {
            KEY_1: [{'start_ts': 5, 'end_ts': 5.5}, {'start_ts': 6, 'end_ts': 7}],
            KEY_2: [{'start_ts': 6, 'end_ts': 7}]
        }
        expected[P.closed(9, 15)] = {
            KEY_1: [{'start_ts': 9, 'end_ts': 15}],
            KEY_2: [{'start_ts': 9, 'end_ts': 15}, {'start_ts': 15.1, 'end_ts': 18}, {'start_ts': 18.1, 'end_ts': 22}]
        }

        overlaps = get_overlaps(grouped_range)
        self.assertEqual(overlaps, expected)