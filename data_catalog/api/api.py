from typing import Optional, Dict, List

import pandas as pd
from bokeh.io import show
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure

from data_catalog.utils.sql.client import MysqlClient

class Api:
    def __init__(self, db_config: Optional[Dict] = None):
        self.client = MysqlClient(db_config)
# TODO should be synced with featurizer and indexer data models
# TODO typing
    def get_meta(
        self,
        exchange: str,
        data_type: str,
        instrument_type: str,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List:
        meta = self.client.select(exchange, data_type, instrument_type, symbol, start_date, end_date)
        ranges = self._make_ranges(meta)
        return ranges

    # TODO sync typing with featurizer
    # TODO util this
    def _make_ranges(self, data: List) -> List[List]:
        # if conseq files differ no more than this, they are in the same range
        # TODO should this be const per data_type?
        SAME_RANGE_DIFF_S = 1
        res = []
        cur_range = []
        for i in range(len(data)):
            cur_range.append(data[i])
            if i < len(data) - 1 and float(data[i + 1]['start_ts']) - float(data[i]['end_ts']) > SAME_RANGE_DIFF_S:
                res.append(cur_range)
                cur_range = []

        if len(cur_range) != 0:
            res.append(cur_range)

        return res

    # TODO util this
    def ranges_to_intervals_df(self, ranges: List):
        intervals = [{'start_ts': float(r[0]['start_ts']), 'end_ts': float(r[-1]['end_ts'])} for r in ranges]
        intervals_df = pd.DataFrame(intervals)
        intervals_df['len_ts'] = intervals_df['end_ts'] - intervals_df['start_ts']

        return intervals_df

    # TODO utils this
    # TODO make this proper work
    # TODO https://docs.bokeh.org/en/3.0.2/docs/examples/basic/bars/intervals.html
    # TODO use stacked hbars https://stackoverflow.com/questions/50417528/bokeh-horizontal-stacked-bar-chart
    def plot_ranges(self, ranges: List):

        # TODO this doesn't need to use df as input?
        cds_df = ColumnDataSource(self.ranges_to_intervals_df(ranges))

        p = figure(x_axis_type='datetime', plot_height=100, plot_width=500)
        p.toolbar_location = None
        p.yaxis.minor_tick_line_color = None

        # p.ygrid[0].ticker.desired_num_ticks = 1

        y1 = p.quad(left='start_ts', right='end_ts', bottom=0, top=1, source=cds_df)

        # output_file(“time_interval.html”, mode =‘cdn’)
        show(p)




