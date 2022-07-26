import json
import os
import plotly.graph_objects as go
from cryptofeed.symbols import str_to_symbol
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

    def get_all_symbol_bases(self):
        bases = []
        for hash in self.data:
            payload_config = self.data[hash]['payload_config']
            exchange = list(payload_config.keys())[0]
            first_channel = list(payload_config[exchange].keys())[0]
            symbol_str = payload_config[exchange][first_channel][0]
            symbol = str_to_symbol(symbol_str)
            if symbol.base not in bases:
                bases.append(symbol.base)

        return bases

    def get_metric(self, type, exch, symbol_base, instrument_type, agg):
        for hash in self.data:
            payload_config = self.data[hash]['payload_config']
            exchange = list(payload_config.keys())[0]
            first_channel = list(payload_config[exchange].keys())[0]
            symbol_str = payload_config[exchange][first_channel][0]
            symbol = str_to_symbol(symbol_str)
            if exch == exchange and symbol.base == symbol_base and symbol.type == instrument_type:
                if 'metrics' not in self.data[hash]:
                    raise ValueError(f'No metrics for {exchange}, {instrument_type}, {symbol_base}')
                return self.data[hash]['metrics'][type]['data-feed-container']['run_duration'][agg][0]

        raise ValueError('Symbol not found')

    # groups data by exchange.instrument_type + symbol bases
    def grouped(self):
        all_bases = self.get_all_symbol_bases()
        grouped = {}
        for hash in self.data:
            if 'metrics' not in self.data[hash]:
                continue
            payload_config = self.data[hash]['payload_config']
            exchange = list(payload_config.keys())[0]
            first_channel = list(payload_config[exchange].keys())[0]
            symbol_str = payload_config[exchange][first_channel][0]
            symbol = str_to_symbol(symbol_str)
            base = symbol.base
            instrument_type = symbol.type
            key = f'{exchange}.{instrument_type}'
            df_mem_metrics = self.data[hash]['metrics']['metrics_server_mem']['data-feed-container']['run_duration']
            item = [base]
            for agg in AGGS:
                item.append(df_mem_metrics[agg][0] if df_mem_metrics[agg][0] is not None else 0)
            if key in grouped:
                grouped[key].append(item)
            else:
                grouped[key] = [item]

        # pad missing bases for each exchange with 0 value metrics
        for base in all_bases:
            for exchange in grouped:
                has_base = False
                for item in grouped[exchange]:
                    if base == item[0]:
                        has_base = True
                if not has_base:
                    item = [base]
                    for _ in AGGS:
                        item.append(0)
                    grouped[exchange].append(item)
        return grouped

    def find_item_in_grouped(self, key, base, grouped):
        for item in grouped[key]:
            if item[0] == base:
                return item
        return None

    def plot_mem(self):
        grouped = self.grouped()
        srtd = {}
        # sort everything according to first exchange p95 memory values
        first_key = list(grouped.keys())[0]

        def make_compare():
            def compare(x, y):
                if isinstance(x, str):
                    base1 = x
                    base2 = y
                else:
                    base1 = x[0]
                    base2 = y[0]
                i1 = self.find_item_in_grouped(first_key, base1, grouped)
                i2 = self.find_item_in_grouped(first_key, base2, grouped)
                # always use p95 for sorting to keep things consistent
                # +1 since symbol is first elem
                _ind = AGGS.index('p95') + 1
                if float(i1[_ind]) < float(i2[_ind]):
                    return -1
                elif float(i1[_ind]) > float(i2[_ind]):
                    return 1
                else:
                    return 0

            return cmp_to_key(compare)

        sorted_bases = sorted(self.get_all_symbol_bases(), key=make_compare())
        for k in grouped:
            # +1 since symbol is first elem
            _ind = AGGS.index(AGG) + 1
            srtd[k] = list(map(lambda e: int(float(e[_ind])/1000.0), sorted(grouped[k], key=make_compare())))
        data = []
        for k in srtd:
            data.append(go.Bar(name=k, x=sorted_bases, y=srtd[k]))
        fig = go.Figure(data=data)
        # Change the bar mode
        fig.update_layout(barmode='group', title_text=f'Memory consumption (aggregation={AGG})')
        fig.show()


re = REResultAnalyzer()
re.load_latest_data()
# print(re.data)
# print(re.grouped())
re.plot_mem()
# print(re.get_metric('metrics_server_mem', 'PHEMEX', 'ETC', 'spot', 'avg'))
# print(re.get_all_symbol_bases())
