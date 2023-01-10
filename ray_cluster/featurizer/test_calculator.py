import calculator as C
# from portion import Interval, IntervalDict
import portion as P
import json


def test_get_ranges_overlaps():
    grouped_range = {}
    ranges_a = P.IntervalDict()
    ranges_a[P.closed(1, 4)] = [meta(1, 2), meta(2.1, 5)]
    ranges_a[P.closed(4.1, 8)] = [meta(5, 5.5), meta(6, 7)]
    ranges_a[P.closed(9, 15)] = [meta(9, 15)]
    grouped_range['feature_a'] = ranges_a

    ranges_b = P.IntervalDict()
    ranges_b[P.closed(2, 5)] = [meta(2, 3), meta(3.1, 6)]
    ranges_b[P.closed(6, 7)] = [meta(6, 7)]
    ranges_b[P.closed(9, 20)] = [meta(9, 15), meta(15.1, 18), meta(18.1, 22)]
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
        'feature_b': [{'start_ts': 9, 'end_ts': 15}, {'start_ts': 15.1, 'end_ts': 18}, {'start_ts': 18.1, 'end_ts': 22}]
    }

    overlaps = C.get_ranges_overlaps(grouped_range)
    assert overlaps == expected
    print(test_get_ranges_overlaps.__name__ + ' passed')

def meta(start_ts, end_ts):
    return {'start_ts': start_ts, 'end_ts': end_ts}

test_get_ranges_overlaps()