import json
import os
import matplotlib.pyplot as plt
import numpy as np
from cryptofeed.symbols import str_to_symbol
from functools import cmp_to_key


AGGS = ['absent', 'avg', 'max', 'min', 'p95']
COLORS = ['r', 'g', 'b', 'c', 'm', 'y', 'k', 'w']

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
                # p95 is last elem, see AGG
                if float(i1[-1]) < float(i2[-1]):
                    return -1
                elif float(i1[-1]) > float(i2[-1]):
                    return 1
                else:
                    return 0

            return cmp_to_key(compare)

        sorted_bases = sorted(self.get_all_symbol_bases(), key=make_compare())
        for k in grouped:
            srtd[k] = list(map(lambda e: int(float(e[-1])/1000.0), sorted(grouped[k], key=make_compare())))

        fig = plt.figure()
        ax = fig.add_axes([0, 0, 1, 1])
        X = np.arange(len(srtd.keys()))
        fig = plt.figure()
        ax = fig.add_axes([0, 0, 1, 1])
        width = 0.25
        accum = 0
        index = 0
        for k in srtd:
            color = COLORS[index % (len(COLORS))]
            ax.bar(X + accum, srtd[k], color=color, width=width)
            accum += width
            index += 1
        plt.show()




re = REResultAnalyzer()
re.load_latest_data()
# print(re.data)
# print(re.grouped())
print(re.plot_mem())
# print(re.get_all_symbol_bases())