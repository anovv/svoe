
def read_parquet() -> None:
    import pandas as pd
    path = 'utils/parquet/parquet_sample_files/COINBASE-BCH-USD-l2_book-1614500246.parquet'
    # table = pq.read_table(path)
    # meta = pq.read_metadata(path)
    # pandas = pq.read_pandas(path)
    # print(pandas)
    df = pd.read_parquet(path)
    print(df.head(3))


def read_s3() -> None:
    import pyarrow.parquet as pq
    import s3fs
    s3 = s3fs.S3FileSystem()
    bucket = 's3://svoe.test.1/parquet/FTX/l2_book/BTC-USD'
    df = pq.ParquetDataset(bucket, filesystem=s3).read_pandas().to_pandas()
    print(df.timestamp)