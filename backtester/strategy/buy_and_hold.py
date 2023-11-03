from typing import List, Optional

from featurizer.feature_stream.feature_stream_generator import DataStreamEvent
from backtester.models.order import Order
from backtester.strategy.base import BaseStrategy


class BuyAndHoldStrategy(BaseStrategy):

    def on_data_udf(self, data_event: DataStreamEvent) -> Optional[List[Order]]:
        raise NotImplementedError