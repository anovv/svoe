import json
import os
import datetime
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from plotly.subplots import make_subplots

from cryptofeed.symbols import str_to_symbol, Symbol

AGG = 'p50'
AGGS = ['absent', 'avg', 'max', 'min', 'p95', 'p50']
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
            for key in data:
                if 'symbol_distribution' in data[key]:
                    symbol_distribution = data[key]['symbol_distribution']
                else:
                    symbol_distribution = UNKNOWN_SYMBOL_DISTRIBUTION
                if symbol_distribution not in self.data:
                    self.data[symbol_distribution] = {}
                self.data[symbol_distribution][key] = data[key]

    def load_latest_data(self):
        latest = self.get_latest_date()
        self.load_data(latest)
        print(f'Loaded data for {latest}')

    def no_metrics(self):
        no_metrics = []
        distr_strategies = list(self.data.keys())
        for symbol_distribution in distr_strategies:
            for key in self.data[symbol_distribution]:
                pod_data = self.data[symbol_distribution][key]
                if 'metrics' not in pod_data:
                    no_metrics.append(pod_data['pod_name'])
        return no_metrics

    # groups data by exchange.instrument_type for each symbols group
    def grouped_perf_metrics(self, symbol_distribution=UNKNOWN_SYMBOL_DISTRIBUTION):
        grouped = {}
        for _key in self.data[symbol_distribution]:
            pod_data = self.data[symbol_distribution][_key]
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
            grouped_by_exchange = self.grouped_perf_metrics(symbol_distribution)
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
            grouped_by_exchange = self.grouped_perf_metrics(symbol_distribution)
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

    # groups data by exchange.instrument_type+channel for each symbol
    def grouped_health_metrics(self, symbol_distribution=UNKNOWN_SYMBOL_DISTRIBUTION):
        grouped = {}
        for _key in self.data[symbol_distribution]:
            pod_data = self.data[symbol_distribution][_key]
            payload_config = pod_data['payload_config']
            exchange = list(payload_config.keys())[0]
            for channel in payload_config[exchange].keys():
                symbols_str = payload_config[exchange][channel]
                symbols = list(map(lambda s: str_to_symbol(s), symbols_str))
                for symbol in symbols:
                    instrument_type = symbol.type
                    key = f'{exchange}.{instrument_type}'
                    item = [symbol.normalized] # symbol + absent + avg
                    if 'metrics' not in pod_data:
                        item.extend([-1, -1])
                    else:
                        health_metrics = pod_data['metrics']['df_health'][channel][symbol.normalized]
                        if health_metrics['absent'][0] is not None:
                            item.append(float(health_metrics['absent'][0]))
                        else:
                            item.append(-1)

                        if health_metrics['avg'][0] is not None:
                            item.append(float(health_metrics['avg'][0]))
                        else:
                            item.append(-1)
                    if key in grouped:
                        if channel in grouped[key]:
                            grouped[key][channel].append(item)
                        else:
                            grouped[key][channel] = [item]
                    else:
                        grouped[key] = {
                            channel: [item]
                        }

        return grouped

    def plot_health(self, symbol_distr):
        start = -1.1
        end = 1.1
        step = 0.1
        subplot_titles = []
        grouped = self.grouped_health_metrics(symbol_distr)
        rows = len(grouped)
        cols = 0
        for exch in grouped:
            cols = max(cols, len(grouped[exch]))

        for exch in grouped:
            for channel in grouped[exch]:
                subplot_titles.append(f'{exch} {channel}')
            if len(grouped[exch]) < cols:
                # pad with empty titles
                for _ in range(cols - len(grouped[exch])):
                    subplot_titles.append('')

        fig = make_subplots(rows=rows, cols=cols, subplot_titles=subplot_titles)
        row = 1
        for exch in grouped:
            col = 1
            for channel in grouped[exch]:
                absent = list(map(lambda e: e[1], grouped[exch][channel]))
                avg = list(map(lambda e: e[2], grouped[exch][channel]))
                fig.add_trace(
                    go.Histogram(x=avg, name=f'{exch}.{channel}', xbins=dict(
                        start=start,
                        end=end,
                        size=step)
                    ),
                    row=row, col=col
                )
                fig.update_xaxes(range=[start, end], row=row, col=col)
                col += 1
            row += 1
        fig.update_layout(title_text=f'Data Feed Channels Health {symbol_distr}', autosize=True, width=2000, height=1000)
        fig.show()


re = REResultAnalyzer()
re.load_latest_data()
# print(re.get_latest_date())
# print(re.grouped_health_metrics('ONE_TO_ONE'))
# print(re.no_metrics())
re.plot_health('ONE_TO_ONE')
