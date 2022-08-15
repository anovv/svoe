
# Represent a feature produced from feature_definition FeatureDefinition and materialized (stored) in Athena
class MaterializedFeature:
    def __init__(self, feature_definition, config):
        self.feature_definition = feature_definition
        self.config = config # contains params applied to FeatureDefinition
        # e.g.
        # {
        #   'exchanges': ['BINANCE', 'FTX']
        #   'symbols': ['BTC-USDT', 'ETH-USDT']
        #   'instrument_types': ['spot', 'perpetual']
        #   'instrument_extras' : [] # in case of options/futures can contain expiry_date/strike_price for specific symbol
        # }
