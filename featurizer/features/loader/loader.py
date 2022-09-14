import featurizer.features.loader.df_utils as dfu
import featurizer.features.loader.l2_snapshot_utils as l2u
import catalog
import dask
import dask.dataframe
import awswrangler as wr
import pandas as pd
import math
import pprint

CHUNK_SIZE = 4  # how many files include in a chunk. Each chunk is an independent dask delayed object


# loads data from s3, takes care of partitioning for dask dataframes based on data_type
# i.e. l2_book deltas need to be partitioned so that each partition contains full book state
class Loader:
    def __init__(self):
        self.dask_cluster = None

    # TODO handle data versioning
    def l2_full(self, exchange, instrument_type, symbol, start, end):
        # TODO are these sorted
        filenames = get_s3_filenames('l2_book', exchange, instrument_type, symbol, start, end)
        chunked_filenames = self._chunk_filenames(filenames)
        ds = [dask.delayed(self._load_and_repartition)(chunk_index) for chunk_index in range(0, len(chunked_filenames))]
        return dask.dataframe.from_delayed(ds)

    def _chunk_filenames(self, filenames):
        return [filenames[i:i + CHUNK_SIZE] for i in range(0, len(filenames), CHUNK_SIZE)]

    def _load_chunk(self, chunk_index, chunked_filenames):
        return dfu._load_df(chunked_filenames[chunk_index], CHUNK_SIZE)

    def _load_and_repartition(self, chunk_index, chunked_filenames):
        # TODO check time diff between chunks to discard long differences
        # load current chunk, load previous/next chunk if needed until full snapshot is restored
        current = self._load_chunk(chunk_index, chunked_filenames)
        prev_index = chunk_index - 1
        next_index = chunk_index + 1
        if not l2u._has_snapshot(current):
            # this will be handled by previous chunk
            return None  # TODO make empty df

        if l2u._starts_with_snapshot(current) and prev_index >= 0:
            # load previous in case it has leftover snapshot data
            previous = self._load_chunk(prev_index, chunked_filenames)
            if l2u._ends_with_snapshot(previous):
                # append previous snapshot data to current head
                prev_end = previous.iloc[-1].name
                prev_last_snapshot_start = l2u._get_snapshot_start(previous, prev_end)
                prev_snapshot = dfu._sub_df(previous, prev_last_snapshot_start, prev_end)
                current = dfu._concat(prev_snapshot, current)

        next = None
        if l2u._ends_with_snapshot(current) and next_index < len(chunked_filenames):
            # to make things even, remove end snapshot from current if it will be handled by next partition
            next = self._load_chunk(next_index, chunked_filenames)
            if l2u._starts_with_snapshot(next):
                # remove cur snapshot data from end
                cur_end = current.iloc[-1].name
                cur_last_snapshot_start = l2u._get_snapshot_start(current, cur_end)
                current = dfu._sub_df(current, 0, cur_last_snapshot_start - 1)

        # append deltas to current until next snapshot is reached
        while next_index < len(chunked_filenames) and (next is None or not l2u._has_snapshot(next)):
            next = self._load_chunk(next_index, chunked_filenames)
            if not l2u._has_snapshot(next):
                current = dfu._concat(current, next)
            next_index += 1
        if l2u._has_snapshot(next):
            next_first_snap_start = l2u._get_first_snapshot_start(next)
            next_deltas = dfu._sub_df(next, 0, next_first_snap_start - 1)
            current = dfu._concat(current, next_deltas)

        # remove all deltas from beginning to make sure we start with snapshot data
        current_first_snap_start = l2u._get_first_snapshot_start(current)
        current = dfu._sub_df(current, current_first_snap_start, current.iloc[-1].name)

        return current

    def test(self):
        filenames_2022_08_03 = [
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-44aa2ce7f07e3ceae09f839a3391d76adb5e75d0/BINANCE*l2_book*BTC-USDT*1659534879.6234548*1659534909.2105565*8e26d2f8b00646feb569b7ee1ad9ab4f.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-44aa2ce7f07e3ceae09f839a3391d76adb5e75d0/BINANCE*l2_book*BTC-USDT*1659534909.3083637*1659534939.0187929*74324787f3bb4efb945cbf55f23b12ce.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-44aa2ce7f07e3ceae09f839a3391d76adb5e75d0/BINANCE*l2_book*BTC-USDT*1659534939.1187956*1659534969.035055*f4d2bfb9c802413cba34aa6c1716ff4b.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-44aa2ce7f07e3ceae09f839a3391d76adb5e75d0/BINANCE*l2_book*BTC-USDT*1659534969.1344223*1659534999.050237*9a0c32bd97234ff6a84e1220f80469ff.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-44aa2ce7f07e3ceae09f839a3391d76adb5e75d0/BINANCE*l2_book*BTC-USDT*1659534999.155565*1659535029.0613592*0b5c1fa43a84450aa185831fa44a95e9.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-44aa2ce7f07e3ceae09f839a3391d76adb5e75d0/BINANCE*l2_book*BTC-USDT*1659535029.1620123*1659535059.076607*2b66aa9fd79948cbb78c51d4720c5483.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-44aa2ce7f07e3ceae09f839a3391d76adb5e75d0/BINANCE*l2_book*BTC-USDT*1659535059.1778233*1659535089.091389*878742d58283427eae790dfd33609f3c.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-551b73ef015edc54438bfdb219710e859e71749c/BINANCE*l2_book*BTC-USDT*1659533678.00125*1659533707.3723602*6456277808494cc3a46cedd8fc45ea48.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-551b73ef015edc54438bfdb219710e859e71749c/BINANCE*l2_book*BTC-USDT*1659533707.4890978*1659533737.3832152*45a8614ddd8b41d688e2e8c1ed5b75b3.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-551b73ef015edc54438bfdb219710e859e71749c/BINANCE*l2_book*BTC-USDT*1659533737.4823482*1659533767.2971497*903f51ffe9254ea0a846df596e3f2139.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-551b73ef015edc54438bfdb219710e859e71749c/BINANCE*l2_book*BTC-USDT*1659533767.3970976*1659533797.3108542*124d4289efcb47dca1162e5bc2f04e90.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-551b73ef015edc54438bfdb219710e859e71749c/BINANCE*l2_book*BTC-USDT*1659534871.1410167*1659534900.5049896*f5b667c567c946b6bcf881611774cd22.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-551b73ef015edc54438bfdb219710e859e71749c/BINANCE*l2_book*BTC-USDT*1659534900.6048121*1659534930.5196357*a47d54a3790848e4b8c1072ff124841f.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-551b73ef015edc54438bfdb219710e859e71749c/BINANCE*l2_book*BTC-USDT*1659534930.6193414*1659534960.5329723*93b9c70070684c92aeba8bb4b0c29f29.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-551b73ef015edc54438bfdb219710e859e71749c/BINANCE*l2_book*BTC-USDT*1659534960.6359491*1659534990.5471883*5fad3fc2caef4b6e8f720412cb49b80a.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-551b73ef015edc54438bfdb219710e859e71749c/BINANCE*l2_book*BTC-USDT*1659534990.645788*1659535020.5620766*b782d4bc04db4578b81ce3d9b2ded04a.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-551b73ef015edc54438bfdb219710e859e71749c/BINANCE*l2_book*BTC-USDT*1659535020.6647966*1659535050.576431*8baeea8c07394e6aabae70a489f98023.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-551b73ef015edc54438bfdb219710e859e71749c/BINANCE*l2_book*BTC-USDT*1659535050.6761158*1659535080.591235*c5d2d7e0c57b4bba870eb8d503dee91b.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-89c8b1195edee7636496a061321113501952d498/BINANCE*l2_book*BTC-USDT*1659530093.4296222*1659530122.801763*81c1eaf43d8948b3a0e3962918fd7cb2.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-89c8b1195edee7636496a061321113501952d498/BINANCE*l2_book*BTC-USDT*1659530122.90108*1659530152.7176547*9edf4d98a3be48d7a244f97f2a7f0128.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-89c8b1195edee7636496a061321113501952d498/BINANCE*l2_book*BTC-USDT*1659530152.8301334*1659530182.8297348*02ef99bfe90a4ca78f2e860f86f7fba2.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-89c8b1195edee7636496a061321113501952d498/BINANCE*l2_book*BTC-USDT*1659530182.929248*1659530212.8432229*03f554b542fa410ab7fb987fb81b84fe.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-89c8b1195edee7636496a061321113501952d498/BINANCE*l2_book*BTC-USDT*1659530212.9446604*1659530242.8561924*f862a0a27da54d4b9150d1a7247aff34.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-89c8b1195edee7636496a061321113501952d498/BINANCE*l2_book*BTC-USDT*1659530242.9558322*1659530272.769038*5f043031b0554757ae801a27c7e2947d.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-89c8b1195edee7636496a061321113501952d498/BINANCE*l2_book*BTC-USDT*1659530272.869734*1659530302.7825155*0a6533ac837145f9b0df2099ec9367f8.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-89c8b1195edee7636496a061321113501952d498/BINANCE*l2_book*BTC-USDT*1659534704.5776105*1659534733.921771*0ab0a8489de74b0b8374f5b5539e21fd.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-89c8b1195edee7636496a061321113501952d498/BINANCE*l2_book*BTC-USDT*1659534734.0228474*1659534763.9353824*0ccbb4c2aefc4915ad5a2cb38386f95c.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-89c8b1195edee7636496a061321113501952d498/BINANCE*l2_book*BTC-USDT*1659534764.0381851*1659534793.9507396*3a8a7814ee444811bff1ebaf4cf21b94.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-89c8b1195edee7636496a061321113501952d498/BINANCE*l2_book*BTC-USDT*1659534794.0509126*1659534823.9653206*1de65fee8fc8476fa270f14fc612510f.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-89c8b1195edee7636496a061321113501952d498/BINANCE*l2_book*BTC-USDT*1659534824.0646224*1659534853.9796023*b63ed097a8a045c085af01bf3b993ff4.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-89c8b1195edee7636496a061321113501952d498/BINANCE*l2_book*BTC-USDT*1659534854.0795298*1659534883.9956083*17d751d9b9c145518eeda4aafa0a9240.gz.parquet',
            's3://svoe.test.1/data_lake/data_feed_market_data/l2_book/exchange=BINANCE/instrument_type=spot/instrument_extra={}/symbol=BTC-USDT/base=BTC/quote=USDT/date=2022-08-03/compaction=raw/version=testing-89c8b1195edee7636496a061321113501952d498/BINANCE*l2_book*BTC-USDT*1659534884.0946796*1659534914.007952*8915bacc10244b7ea741045973312c3f.gz.parquet'
        ]
        pp = pprint.PrettyPrinter()
        sorted_filenames, has_overlap = catalog.get_sorted_filenames('l2_book', 'BINANCE', 'spot', 'BTC-USDT', '2022-08-03', '2022-08-03')
        grouped_filenames, has_overlap = catalog.get_grouped_filenames('l2_book', 'BINANCE', 'spot', 'BTC-USDT', '2022-08-03', '2022-08-03')
        print(len(grouped_filenames))
        catalog.plot_filename_ranges(grouped_filenames[1])

loader = Loader()
loader.test()
