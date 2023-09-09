import datetime
from typing import Dict, List, Tuple

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from simulation.models.instrument import Instrument
from simulation.models.order import OrderSide
from simulation.models.portfolio import PortfolioBalanceRecord
from simulation.models.trade import Trade


class Visualizer:

    def __init__(
        self,
        executed_trades: Dict[Instrument, List[Trade]],
        portfolio_balances: List[PortfolioBalanceRecord],
        sampled_prices: Dict[Instrument, List[Tuple[float, float]]]
    ):
        self.executed_trades = executed_trades
        self.portfolio_balances = portfolio_balances
        self.sampled_prices = sampled_prices

    # https://medium.com/geekculture/are-you-a-beginner-in-trading-build-your-first-trading-strategy-with-python-95fef3b313ab
    def visualize(self, instruments: List[Instrument], include_total: bool = True):
        num_subplots = len(instruments)
        if include_total:
            num_subplots += 1

        fig = make_subplots(rows=num_subplots, cols=1)
        start_pos = 1
        if include_total:
            totals = [b.total for b in self.portfolio_balances]
            totals_timestamps = [datetime.datetime.utcfromtimestamp(b.timestamp) for b in self.portfolio_balances]
            total_trace = go.Scatter(
                x=totals_timestamps,
                y=totals,
                name='Total balance'
            )
            fig.add_trace(total_trace, start_pos, 1)
            start_pos += 1

        for instrument in instruments:
            prices_timestamps = [datetime.datetime.utcfromtimestamp(p[0]) for p in self.sampled_prices[instrument]]
            prices = [p[1] for p in self.sampled_prices[instrument]]
            prices_trace = go.Scatter(
                x=prices_timestamps,
                y=prices,
                name=f'Price {instrument}'
            )
            fig.add_trace(prices_trace, start_pos, 1)

            buy_trades_timestamps = [datetime.datetime.utcfromtimestamp(t.timestamp) for t in self.executed_trades[instrument] if t.side == OrderSide.BUY]
            buy_trades_prices = [t.price for t in self.executed_trades[instrument] if t.side == OrderSide.BUY]
            buy_trace = go.Scatter(
                x=buy_trades_timestamps,
                y=buy_trades_prices,
                name=f'Buy {instrument}',
                mode='markers',
                marker=dict(symbol='triangle-up', size=12),
                hovertemplate=('BUY on %{x}')
            )
            fig.add_trace(buy_trace, start_pos, 1)
            sell_trades_timestamps = [datetime.datetime.utcfromtimestamp(t.timestamp) for t in self.executed_trades[instrument] if t.side == OrderSide.SELL]
            sell_trades_prices = [t.price for t in self.executed_trades[instrument] if t.side == OrderSide.SELL]
            sell_trace = go.Scatter(
                x=sell_trades_timestamps,
                y=sell_trades_prices,
                name=f'Sell {instrument}',
                mode='markers',
                marker=dict(symbol='triangle-down', size=12),
                hovertemplate=('SELL on %{x}')
            )
            fig.add_trace(sell_trace, start_pos, 1)
            start_pos += 1

        # TODO time axis are not scaled properly between graphs
        fig.show()
