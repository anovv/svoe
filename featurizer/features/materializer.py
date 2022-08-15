
# Represent service transforming FeatureDefinition -> MaterializedFeature based on user input
class Materializer:
    def __init__(self):
        self.dask_cluster = None

    def launch_dask_cluster(self, spec):
        # Should check if cluster exists and launch based on spec
        self.dask_cluster = None

    def materialize(self, args):
        # args:
        # {
        #   'FeatureDefinitionA': {
        #       'params': {
        #           'exchnages': ['BINANCE']
        #           'symbols': ['BTC-USDT']
        #           'instrument_type': ['spot']
        #       }
        #   }
        # }
        return # should return list of MaterializedFeature objects