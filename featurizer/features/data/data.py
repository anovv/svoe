# a placeholder class to indicte that all subclasses are raw data channels
class Data:

    @classmethod
    def type_str(cls) -> str:
        return cls.__name__

    # this is a hacky way to discern between types in Union[FeatureDefinition, Data]
    # without isinstance (due to python bug)
    @classmethod
    def is_data(cls) -> bool:
        return True

    @classmethod
    def params(cls):
        raise NotImplemented

