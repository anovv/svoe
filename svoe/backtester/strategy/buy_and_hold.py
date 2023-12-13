from typing import List, Optional

from svoe.featurizer.streaming.offline_feature_stream_generator import DataStreamEvent
from svoe.backtester.models.order import Order
from svoe.backtester.strategy.base import BaseStrategy


class BuyAndHoldStrategy(BaseStrategy):

    def on_data_udf(self, data_event: DataStreamEvent) -> Optional[List[Order]]:
        raise NotImplementedError