from svoe.featurizer.data_definitions.data_definition import EventSchema
from svoe.featurizer.data_definitions.data_source_definition import DataSourceDefinition


class CryptofeedTradesData(DataSourceDefinition):

    @classmethod
    def event_schema(cls) -> EventSchema:
        return {
            'timestamp': float,
            'receipt_timestamp': float,
            'side': str,
            'amount': float,
            'price': float,
            'id': str,
            # 'trades': List[Dict] # side, amount, price, id
        }