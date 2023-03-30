import unittest

from utils.pandas.df_utils import store_df


class TestDfUtils(unittest.TestCase):

    def test_store_df(self):
        # TODO
        print(store_df('', None))


if __name__ == '__main__':
    t = TestDfUtils()
    t.test_store_df()