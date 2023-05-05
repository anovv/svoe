from featurizer.features.data.data_definition import DataDefinition

# TODO remove this and DataDefinition, keep only FeatureDefinition?
# represents raw datasource
class DataSourceDefinition(DataDefinition):

    @classmethod
    def is_data_source(cls) -> bool:
        return True

