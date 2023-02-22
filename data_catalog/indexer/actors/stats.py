import functools
from time import time
from typing import Dict, List, Callable

import tornado
from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from bokeh.server.server import Server
from bokeh.models import ColumnDataSource, DataRange1d
from bokeh.plotting import figure
from ray.types import ObjectRef

import ray

# for async wait/signaling see last comment https://github.com/ray-project/ray/issues/7229

# counter names
# TODO enum
from tornado.ioloop import IOLoop

DOWNLOAD_TASKS = 'download_tasks'
INDEX_TASKS = 'index_tasks'
DB_READS = 'db_reads'
DB_WRITES = 'db_writes'

# consts
TIME = 'time'


@ray.remote
class Stats:
    def __init__(self,):
        self.state = {
            DOWNLOAD_TASKS: 0,
            INDEX_TASKS: 0,
            'download_queue_size': 0,
            'index_queue_size': 0,
            'store_queue_size': 0,
            DB_READS: 0,
            DB_WRITES: 0
        }
        data_source_params = dict(zip(self.state.keys(), [[0] for _ in range(len(self.state.values()))]))
        data_source_params[TIME] = [time()]
        self.data_source = ColumnDataSource(data_source_params)

    # def wait_and_update_counter(self, ref: ObjectRef, counter_name: str):
    #     ray.wait([ref])
    #     self.update_counter(counter_name)

    def inc_counter(self, counter_name: str):
        self.state[counter_name] += 1
        data = self.state.copy()
        data[TIME] = time()
        for k in data:
            data[k] = [data[k]]
        self.data_source.stream(data)

    def poll_queues_states(self):
        pass

    def poll_cluster_state(self):
        pass

    # TODO this should be on a separate thread
    def run(self):
        # start bokeh server
        apps = {'/': Application(FunctionHandler(functools.partial(_make_bokeh_doc, source=self.data_source)))}
        # apps = {'/': Application(FunctionHandler(make_test_document))}
        server = Server(apps, port=5001)
        server.start()
        IOLoop.current().start()


def make_test_document(doc):
    fig = figure(title='Line plot!', sizing_mode='scale_width')
    fig.line(x=[1, 2, 3], y=[1, 4, 9])
    doc.title = "Hello, world!"
    doc.add_root(fig)


def _make_bokeh_doc(doc, source):
    x_range = DataRange1d(follow='end', follow_interval=20000, range_padding=0)
    fig = figure(title="Data",
                 x_axis_type='datetime', y_range=[-0.1, 100 + 0.1], # TODO 100
                 height=150, tools='', x_range=x_range)
    fig.line(source=source, x=TIME, y=DOWNLOAD_TASKS, color='red')
    fig.line(source=source, x=TIME, y=INDEX_TASKS, color='green')
    fig.line(source=source, x=TIME, y=DB_READS, color='blue')
    fig.line(source=source, x=TIME, y=DB_WRITES, color='yellow')
    fig.yaxis.minor_tick_line_color = None

    # fig.add_tools(
    #     ResetTool(reset_size=False),
    #     PanTool(dimensions="width"),
    #     WheelZoomTool(dimensions="width")
    # )
    doc.title = "Indexer State"
    doc.add_root(fig)

