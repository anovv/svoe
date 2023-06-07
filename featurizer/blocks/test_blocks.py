import unittest

import pandas as pd
import portion as P

from featurizer.blocks.blocks import get_overlaps, mock_meta, prune_overlaps, lookahead_shift


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

        expected = {}
        expected[P.closed(2, 4)] = {
            KEY_1: [mock_meta(1, 2), mock_meta(2.1, 5)],
            KEY_2: [mock_meta(2, 3), mock_meta(3.1, 6)]
        }
        expected[P.closed(4.1, 5)] = {
            KEY_1: [mock_meta(5, 5.5), mock_meta(6, 7)],
            KEY_2: [mock_meta(2, 3), mock_meta(3.1, 6)]
        }
        expected[P.closed(6, 7)] = {
            KEY_1: [mock_meta(5, 5.5), mock_meta(6, 7)],
            KEY_2: [mock_meta(6, 7)]
        }
        expected[P.closed(9, 15)] = {
            KEY_1: [mock_meta(9, 15)],
            KEY_2: [mock_meta(9, 15), mock_meta(15.1, 18), mock_meta(18.1, 22)]
        }

        overlaps = get_overlaps(grouped_range)
        self.assertEqual(overlaps, expected)

    def test_pruned_overlaps(self):
        KEY_1 = 'key_1'
        KEY_2 = 'key_2'
        grouped_range = {}
        ranges_a = P.IntervalDict()
        ranges_a[P.closed(1, 3)] = [mock_meta(1, 1.9), mock_meta(2.1, 3)]
        ranges_a[P.closed(5, 7)] = [mock_meta(5, 6.1), mock_meta(6.2, 7)]
        ranges_a[P.closed(9, 16)] = [mock_meta(9, 16)]
        grouped_range[KEY_1] = ranges_a

        ranges_b = P.IntervalDict()
        ranges_b[P.closed(2, 4)] = [mock_meta(2, 3), mock_meta(3.1, 4)]
        ranges_b[P.closed(6, 7)] = [mock_meta(6, 7)]
        ranges_b[P.closed(8, 22)] = [mock_meta(8, 15), mock_meta(15.1, 18), mock_meta(18.1, 22)]
        grouped_range[KEY_2] = ranges_b

        expected = {}
        expected[P.closed(2, 3)] = {
            KEY_1: [mock_meta(2.1, 3)],
            KEY_2: [mock_meta(2, 3)]
        }
        expected[P.closed(6, 7)] = {
            KEY_1: [mock_meta(5, 6.1), mock_meta(6.2, 7)],
            KEY_2: [mock_meta(6, 7)]
        }
        expected[P.closed(9, 16)] = {
            KEY_1: [mock_meta(9, 16)],
            KEY_2: [mock_meta(8, 15), mock_meta(15.1, 18)]
        }

        pruned_overlaps = prune_overlaps(get_overlaps(grouped_range))
        self.assertEqual(pruned_overlaps, expected)

    def test_look_ahead_shift(self):
        lookahead = '3s'
        a_ts = [1, 2, 3, 5, 8, 9, 20, 21, 22, 23, 28, 31, 32, 33, 34, 40, 41, 42, 46]
        a_vals = [f'val{ts}' for ts in a_ts]
        df = pd.DataFrame({'timestamp': a_ts, 'vals': a_vals})

        b_ts = [3, 5, 5, 8, 9, 9, 23, 23, 23, 23, 31, 34, 34, 34, 34, 42, 42, 42]
        b_vals = [f'val{ts}' for ts in b_ts]
        expected_df = pd.DataFrame({'timestamp': b_ts, 'vals': b_vals})

        res = lookahead_shift(df, lookahead)
        print(res)

        assert expected_df.equals(res)


if __name__ == '__main__':
    t = TestBlocks()

    # t.test_overlaps()
    # t.test_pruned_overlaps()
    t.test_look_ahead_shift()