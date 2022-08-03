import json
import os
import datetime
import plotly.graph_objects as go
import numpy as np
from plotly.subplots import make_subplots
import plotly.express as px

from cryptofeed.symbols import str_to_symbol, Symbol
from functools import cmp_to_key

AGG = 'p95'
AGGS = ['absent', 'avg', 'max', 'min', 'p95']
UNKNOWN_SYMBOL_DISTRIBUTION = 'UNKNOWN_SYMBOL_DISTRIBUTION'

class REResultAnalyzer:
    def __init__(self):
        self.data = {} # grouped by symbol_distribution

    def get_latest_date(self):
        dates = []
        for f in os.listdir("."):
            if os.path.isdir(f):
                dates.append(f)
        dates.remove('__pycache__')
        dates = sorted(dates, key=lambda x: datetime.datetime.strptime(x, '%d-%m-%Y-%H-%M-%S'))
        return dates[-1]

    def load_data(self, date):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        file_path = dir_path + f'/{date}/resources-estimation.json'
        with open(file_path) as json_file:
            data = json.load(json_file)
            for hash in data:
                if 'symbol_distribution' in data[hash]:
                    symbol_distribution = data[hash]['symbol_distribution']
                else:
                    symbol_distribution = UNKNOWN_SYMBOL_DISTRIBUTION
                if symbol_distribution not in self.data:
                    self.data[symbol_distribution] = {}
                self.data[symbol_distribution][hash] = data[hash]

    def load_latest_data(self):
        latest = self.get_latest_date()
        self.load_data(latest)
        print(f'Loaded data for {latest}')

    # groups data by exchange.instrument_type for each symbols group
    def grouped_by_exchange(self, symbol_distribution=UNKNOWN_SYMBOL_DISTRIBUTION):
        # all_symbol_groups = self.get_all_symbol_groups(symbol_distribution)
        grouped = {}
        for hash in self.data[symbol_distribution]:
            pod_data = self.data[symbol_distribution][hash]
            payload_config = pod_data['payload_config']
            exchange = list(payload_config.keys())[0]
            first_channel = list(payload_config[exchange].keys())[0]
            symbols_str = payload_config[exchange][first_channel]
            symbols = list(map(lambda s: str_to_symbol(s), symbols_str))
            instrument_type = symbols[0].type
            key = f'{exchange}.{instrument_type}'
            item = [symbols]
            if 'metrics' not in pod_data:
                for _ in AGGS:
                    item.append(0)
            else:
                df_mem_metrics = pod_data['metrics']['metrics_server_mem']['data-feed-container']['run_duration']
                for agg in AGGS:
                    item.append(df_mem_metrics[agg][0] if df_mem_metrics[agg][0] is not None else 0)
            if key in grouped:
                grouped[key].append(item)
            else:
                grouped[key] = [item]

        return grouped

    def plot_mem(self):
        distr_strategies = list(self.data.keys())
        exchange_instruments = set()
        subplot_titles = []
        for symbol_distribution in distr_strategies:
            grouped_by_exchange = self.grouped_by_exchange(symbol_distribution)
            for exchange_instrument in grouped_by_exchange:
                exchange_instruments.add(exchange_instrument)

        for _ in distr_strategies:
            subplot_titles.extend(list(exchange_instruments))

        fig = make_subplots(
            rows=len(distr_strategies), cols=len(exchange_instruments), subplot_titles=subplot_titles
        )
        row = 1
        for symbol_distribution in distr_strategies:
            col = 1
            grouped_by_exchange = self.grouped_by_exchange(symbol_distribution)
            for exchange_instrument in exchange_instruments:
                symbol_groups_str = []
                metric_values = []
                for item in grouped_by_exchange[exchange_instrument]:
                    symbol_groups_str.append(str(item[0]))
                    # +1 since symbol is first elem
                    _ind = AGGS.index(AGG) + 1
                    metric_value = int(float(item[_ind])/1000.0)
                    metric_values.append(metric_value)
                fig.add_trace(go.Bar(x=symbol_groups_str, y=metric_values), row=row, col=col)
                col += 1
            row += 1
        # Change the bar mode
        fig.update_layout(title_text=f'Memory consumption (aggregation={AGG})', autosize=True, width=2000, height=2000)
        fig.show()


re = REResultAnalyzer()
re.load_latest_data()
# print(re.get_latest_date())
# print(re.grouped_by_exchange('LARGEST_WITH_SMALLEST')['BINANCE_FUTURES.perpetual'])
re.plot_mem()
# print(px.data.tips())
# print(re.get_metric('metrics_server_mem', 'BINANCE', 'ETC-USDT', 'spot', 'avg'))
# print(re.get_all_symbol_groups())
