import joblib
import pandas as pd

from utils.pandas.df_utils import get_cached_df, load_df


# def mock_raw_cryptotick_df(
#     path: str = 's3://svoe-cryptotick-data/trades/20230201/BINANCE_SPOT_BTC_USDT.csv.gz',
#     split_size_kb: int = 100 * 1024
# ) -> pd.DataFrame:
#     print('Loading mock cryptotick df...')
#     key_proc = joblib.hash(f'{path}_proc_{split_size_kb}')
#     proc_df = get_cached_df(key_proc)
#     if proc_df is not None:
#         print('Mock cryptotick df cached')
#         return proc_df
#     raw_df = load_df(path)
#     proc_df = preprocess_l2_inc_df(raw_df, date_str)
#     if split_size_kb < 0:
#         split = proc_df
#     else:
#         split_gen = gen_split_df_by_mem(proc_df, split_size_kb)
#         split = next(split_gen)
#     cache_df_if_needed(split, key_proc)
#     print('Done loading mock cryptotick df')
#     return split