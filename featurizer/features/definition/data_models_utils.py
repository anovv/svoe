from dataclasses import dataclass


@dataclass
class TimestampedBase:
    timestamp: float
    receipt_timestamp: float