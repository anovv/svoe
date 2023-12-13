import pandas as pd

from svoe.featurizer.data_ingest.utils.cryptotick_utils import process_cryptotick_timestamps


def preprocess_trades_df(df: pd.DataFrame) -> pd.DataFrame:
    df = process_cryptotick_timestamps(df)
    df = df.drop(columns=['id_exch_guid', 'id_exch_int_inc', 'order_id_maker', 'order_id_taker'])
    df = df.rename(columns={'base_amount': 'amount', 'taker_side': 'side', 'guid': 'id'})

    df = df.reset_index(drop=True)

    return df
