import json
import os
import plotly.graph_objects as go
from cryptofeed.symbols import str_to_symbol, Symbol
from functools import cmp_to_key

AGG = 'avg'
AGGS = ['absent', 'avg', 'max', 'min', 'p95']

class REResultAnalyzer:
    def __init__(self):
        self.data = {}

    def get_latest_date(self):
        dates = []
        for f in os.listdir("."):
            if os.path.isdir(f):
                dates.append(f)
        dates.remove('__pycache__')
        dates.sort()
        return dates[-1]

    def load_data(self, date):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        file_path = dir_path + f'/{date}/resources-estimation.json'
        with open(file_path) as json_file:
            self.data = json.load(json_file)

    def load_latest_data(self):
        latest = self.get_latest_date()
        self.load_data(latest)
        print(f'Loaded data for {latest}')

    def symbols_equal(self, s1, s2):
        same = s1.quote == s2.quote and s1.type == s2.type
        # treat usd and usdt base as equal
        return same and (s1.base == s2.base or (s1.base in ('USD', 'USDT') and s2.base in ('USD', 'USDT')))

    def symbol_groups_equal(self, g1, g2):
        # assume no duplicates
        if not len(g1) == len(g2):
            return False
        for s1 in g1:
            eq = False
            for s2 in g2:
                if self.symbols_equal(s1, s2):
                    eq = True
                    break
            if not eq:
                return False
        return True

    def get_all_symbol_groups(self):
        groups = []
        for hash in self.data:
            payload_config = self.data[hash]['payload_config']
            exchange = list(payload_config.keys())[0]
            first_channel = list(payload_config[exchange].keys())[0]
            symbols_str = payload_config[exchange][first_channel]
            symbols = list(map(lambda s: str_to_symbol(s), symbols_str))
            has = False
            for g in groups:
                if self.symbol_groups_equal(symbols, g):
                    has = True
                    break
            if not has:
                groups.append(symbols)

        return groups

    def get_metric(self, metric_type, exch, symbol_str, instrument_type, agg):
        for hash in self.data:
            payload_config = self.data[hash]['payload_config']
            exchange = list(payload_config.keys())[0]
            first_channel = list(payload_config[exchange].keys())[0]
            symbols_str = payload_config[exchange][first_channel]
            symbols = list(map(lambda s: str_to_symbol(s), symbols_str))
            if exch == exchange and symbol_str in symbols_str and instrument_type == symbols[0].type:
                if 'metrics' not in self.data[hash]:
                    raise ValueError(f'No metrics for {exchange}, {instrument_type}, {symbol_str}')
                return self.data[hash]['metrics'][metric_type]['data-feed-container']['run_duration'][agg][0]

        raise ValueError('Symbol not found')

    # groups data by exchange.instrument_type for each symbols group
    def grouped_by_exchange(self):
        all_symbol_groups = self.get_all_symbol_groups()
        grouped = {}
        for hash in self.data:
            if 'metrics' not in self.data[hash]:
                continue
            payload_config = self.data[hash]['payload_config']
            exchange = list(payload_config.keys())[0]
            first_channel = list(payload_config[exchange].keys())[0]
            symbols_str = payload_config[exchange][first_channel]
            symbols = list(map(lambda s: str_to_symbol(s), symbols_str))
            instrument_type = symbols[0].type
            key = f'{exchange}.{instrument_type}'
            df_mem_metrics = self.data[hash]['metrics']['metrics_server_mem']['data-feed-container']['run_duration']
            item = [symbols]
            for agg in AGGS:
                item.append(df_mem_metrics[agg][0] if df_mem_metrics[agg][0] is not None else 0)
            if key in grouped:
                grouped[key].append(item)
            else:
                grouped[key] = [item]

        # pad missing bases for each exchange with 0 value metrics
        for g in all_symbol_groups:
            for exchange in grouped:
                has = False
                for item in grouped[exchange]:
                    if self.symbol_groups_equal(g, item[0]):
                        has = True
                if not has:
                    item = [g]
                    for _ in AGGS:
                        item.append(0)
                    grouped[exchange].append(item)
        return grouped

    def find_item(self, key, symbol_group, grouped_by_exchange):
        for item in grouped_by_exchange[key]:
            if self.symbol_groups_equal(item[0], symbol_group):
                return item
        return None

    def plot_mem(self):
        grouped_by_exchange = self.grouped_by_exchange()
        srtd = {}
        # sort everything according to first exchange p95 memory values
        first_key = list(grouped_by_exchange.keys())[0]

        # smallest to largest
        def compare(x, y):
            if isinstance(x[0], str) or isinstance(x[0], Symbol):
                g1 = x
                g2 = y
            else:
                g1 = x[0]
                g2 = y[0]
            i1 = self.find_item(first_key, g1, grouped_by_exchange)
            i2 = self.find_item(first_key, g2, grouped_by_exchange)
            # always use p95 for sorting to keep things consistent
            # +1 since symbol is first elem
            _ind = AGGS.index('p95') + 1
            if float(i1[_ind]) < float(i2[_ind]):
                return -1
            elif float(i1[_ind]) > float(i2[_ind]):
                return 1
            else:
                return 0
        sorted_groups = sorted(self.get_all_symbol_groups(), key=cmp_to_key(compare), reverse=True)
        sorted_groups_str = list(map(lambda g: str(list(map(lambda s: s.normalized, g))), sorted_groups))
        for k in grouped_by_exchange:
            # +1 since symbol is first elem
            _ind = AGGS.index(AGG) + 1
            srtd[k] = list(map(lambda g: int(float(self.find_item(k, g, grouped_by_exchange)[_ind])/1000.0), sorted_groups))
        data = []
        for k in srtd:
            data.append(go.Bar(name=k, x=sorted_groups_str, y=srtd[k]))
        fig = go.Figure(data=data)
        # Change the bar mode
        fig.update_layout(barmode='group', title_text=f'Memory consumption (aggregation={AGG})')
        fig.show()


re = REResultAnalyzer()
re.load_latest_data()
# print(re.data)
# print(re.grouped_by_exchange())
re.plot_mem()
# print(re.get_metric('metrics_server_mem', 'BINANCE', 'ETC-USDT', 'spot', 'avg'))
# print(re.get_all_symbol_groups())
