import unittest
from data_catalog.indexer.indexer import Indexer
from data_catalog.indexer.sql.client import MysqlClient
from data_catalog.indexer.sql.models import add_defaults
from data_catalog.indexer.tasks.tasks import _index_df
from data_catalog.indexer.util import generate_input_items
from utils.pandas.df_utils import load_dfs


class TestDataCatalogIndexer(unittest.TestCase):

    def test_parse_s3_keys(self):
        # TODO add multiproc
        exchange_symbol_unique_pairs = set()
        for _ in range(5):
            batch = next(generate_input_items(1000))
            for i in batch:
                exchange_symbol_unique_pairs.add((i['exchange'], i['symbol']))
        print(exchange_symbol_unique_pairs)

    def test_db_client(self):
        batch_size = 1
        batch = next(generate_input_items(batch_size))
        client = MysqlClient()
        client.create_tables()
        not_exist = client.check_exists(batch)
        print(f'Found {batch_size - len(not_exist)} items in db, {len(not_exist)} to write')
        dfs = load_dfs([i['path'] for i in not_exist])
        index_items = []
        for df, i in zip(dfs, not_exist):
            index_items.append(add_defaults(_index_df(df, i)))
        write_res = client.write_index_item_batch(index_items)
        print(f'Written {len(index_items)} to db, checking again...')
        not_exist = client.check_exists(batch)
        print(f'Found {batch_size - len(not_exist)} existing records in db')

    def test_indexer(self):
        # TODO start ray cluster
        indexer = Indexer()
        indexer.run()
        # TODO stop ray cluster

if __name__ == '__main__':
    t = TestDataCatalogIndexer()
    t.test_db_client()