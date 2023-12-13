from svoe.featurizer.data_definitions.data_definition import EventSchema
from svoe.featurizer.data_definitions.data_source_definition import DataSourceDefinition


class CryptofeedTickerData(DataSourceDefinition):

    @classmethod
    def event_schema(cls) -> EventSchema:
        return {
            'timestamp': float,
            'receipt_timestamp': float,
            'bid': float,
            'ask': float,
        }
