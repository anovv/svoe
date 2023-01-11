# a placeholder class to indicte that all subclasses are raw data channels
class Data:

    @classmethod
    def type_str(cls) -> str:
        return cls.__name__

    @classmethod
    def params(cls):
        raise NotImplemented

