import sys
sys.path.append('/Users/anov/IdeaProjects/cryptofeed')
sys.path.append('/Users/anov/IdeaProjects/cryptostore')

from configs.data_feed.kubernetes_config_builder import KubernetesConfigBuilder
from configs.data_feed.cryptostore_config_builder import CryptostoreConfigBuilder
from configs.data_feed.base_config_builder import BaseConfigBuilder
from data_feed.data_feed_service import DataFeedService

def test():
    #
    # kcb = KubernetesConfigBuilder()
    # print(kcb.gen())
    # ccb = CryptostoreConfigBuilder()
    # print(ccb.gen_DEBUG())
    DataFeedService.run()
    # read_s3()

if __name__ == '__main__':
    test()
