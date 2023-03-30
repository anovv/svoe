import unittest

from utils.s3.s3_utils import list_files_and_sizes_kb


class TestS3Utils(unittest.TestCase):

    def test_list_files(self):
        files_and_sizes = list_files_and_sizes_kb('svoe-cryptotick-data')
        print(files_and_sizes[:10])


if __name__ == '__main__':
    t = TestS3Utils()
    t.test_list_files()