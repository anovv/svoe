from typing import Type

from featurizer.data_definitions.data_definition import DataDefinition
from featurizer.feature_stream.event_emitter.data_source_event_emitter import DataSourceEventEmitter


# TODO remove this and DataDefinition, keep only FeatureDefinition?
# represents raw datasource
class DataSourceDefinition(DataDefinition):

    @classmethod
    def is_data_source(cls) -> bool:
        return True

    @classmethod
    def is_synthetic(cls) -> bool:
        return False

    @classmethod
    def event_emitter_type(cls) -> Type[DataSourceEventEmitter]:
        raise NotImplementedError