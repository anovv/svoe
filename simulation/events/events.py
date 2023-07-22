from simulation.models.instrument import Instrument


# TODO sync this with events in featurizer
class DataEvent:
    timestamp: float
    instrument: Instrument
    data_type: str

