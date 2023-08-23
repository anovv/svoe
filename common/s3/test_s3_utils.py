import unittest

from common.s3.s3_utils import list_files_and_sizes_kb, download_dir


class TestS3Utils(unittest.TestCase):

    def test_list_files(self):
        files_and_sizes = list_files_and_sizes_kb('svoe-cryptotick-data')
        print(files_and_sizes[:10])

    def test_download_dir(self):
        temp_dir, local_files = download_dir(s3_path='s3://svoe-feature-definitions/0/test_feature_group/test_feature_definition/1/')
        print(local_files)
        temp_dir.cleanup()


if __name__ == '__main__':
    t = TestS3Utils()
    t.test_download_dir()