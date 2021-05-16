# import sys
# sys.path.append('/Users/anov/IdeaProjects/cryptofeed')
# sys.path.append('/Users/anov/IdeaProjects/cryptostore')

from configs.data_feed.kubernetes_config_builder import KubernetesConfigBuilder
from configs.data_feed.cryptostore_config_builder import CryptostoreConfigBuilder
from data_feed.data_feed_service import DataFeedService

def test():
    #
    # kcb = KubernetesConfigBuilder()
    ccb = CryptostoreConfigBuilder()
    # print(kcb.data_feed_config_map())
    # print(kcb.data_feed_stateful_set())
    print(ccb.cryptostore_single_config_DEBUG())

    DataFeedService.run()
    # read_s3()
    # ConfigBuilder.get_bitmex_pairs()

if __name__ == '__main__':
    test()
