from streamz import Stream


# Represent a feature schema to be used with different params (exchanges, symbols, instrument_types, etc)
# each set of params producing materialized feature
class FeatureDefinition:

    @staticmethod
    def stream(upstream: Stream) -> Stream:
        raise ValueError('Not Implemented')
    # channels used to calculate this feature
    # e.g.
    # {
    #   'l2_book': 2,
    #   'ticker': 1
    # }
    # means this feature operates with 2 different l2_books and 1 ticker
    # def channels_spec(self):
    #     raise ValueError('Not Implemented')
    #
    # def transform(self, input_dfs):
    #     raise ValueError('Not Implemented')
    #
    # def _transform_dask(self, ranges):
    #     # This should contain logic of parallelizing transform on a Dask Cluster for given time ranges
    #     return
    #
    # def _materialize(self, ranges):
    #     # This should contain logic of running dask transform with saving result to Athena and updating feature index
    #     return

# check https://github.com/bukosabino/ta
