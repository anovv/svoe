# example 's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-44aa2ce7f07e3ceae09f839a3391d76adb5e75d0/
# BINANCE*l2_book*BTC-USDT*1659534879.6234548*1659534909.2105565*8e26d2f8b00646feb569b7ee1ad9ab4f.gz.parquet',
#

def _time_range(filename):
    split = filename.split('*')
    start = float(split[3])
    end = float(split[4])
    return end - start, start, end

def _has_overlap(f1, f2):
    # https://github.com/brentp/interlap
    # https://pypi.org/project/intervaltree/
    return True

def _is_sorted(filenames):
    return True

def _get_time_diff(f1, f2):
    if f1 is None or f2 is None:
        return 0
    _, start1, _ = _time_range(f1)
    _, start2, _ = _time_range(f2)

    return start1 - start2
