# import sys
# sys.path.append('/Users/anov/IdeaProjects/cryptofeed')
# sys.path.append('/Users/anov/IdeaProjects/cryptostore')

from configs.data_feed.kubernetes_config_builder import KubernetesConfigBuilder

def test():
    #
    kcb = KubernetesConfigBuilder()
    print(kcb.data_feed_config_map())
    print(kcb.data_feed_stateful_set())
    # DataFeedService.run()
    # read_s3()
    # ConfigBuilder.get_bitmex_pairs()

if __name__ == '__main__':
    test()