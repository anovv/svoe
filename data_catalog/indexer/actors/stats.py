import functools
from threading import Thread
from time import time
from typing import Dict, List, Callable

import tornado
from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from bokeh.server.server import Server
from bokeh.models import ColumnDataSource, DataRange1d, ResetTool, PanTool, WheelZoomTool
from bokeh.plotting import figure
from ray.types import ObjectRef

import ray

# for async wait/signaling see last comment https://github.com/ray-project/ray/issues/7229
# for streaming to Bokeh https://matthewrocklin.com/blog/work/2017/06/28/simple-bokeh-server
# for threaded updates https://stackoverflow.com/questions/55176868/asynchronous-streaming-to-embedded-bokeh-server

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
    def __init__(self):
        self.plot_data = [{
            TIME: [time() * 1000],
            DOWNLOAD_TASKS: [0],
            INDEX_TASKS: [0],
            'download_queue_size': [0],
            'index_queue_size': [0],
            'store_queue_size': [0],
            DB_READS: [0],
            DB_WRITES: [0]
        }]
        self.last_data_length = None

    def inc_counter(self, counter_name: str):
        new_event = {}
        last_event = self.plot_data[-1]
        for _counter_name in last_event:
            if _counter_name == TIME:
                new_event[TIME] = [time() * 1000]
            elif _counter_name == counter_name:
                new_event[_counter_name] = [last_event[_counter_name][0] + 1]
            else:
                new_event[_counter_name] = [last_event[_counter_name][0]]
        self.plot_data.append(new_event)


    def poll_queues_states(self):
        pass

    def poll_cluster_state(self):
        pass

    def run(self):
        def _run_loop():
            # start bokeh server
            apps = {'/': Application(FunctionHandler(functools.partial(self._make_bokeh_doc, update=self._update)))}
            loop = tornado.ioloop.IOLoop()
            server = Server(apps, io_loop=loop, port=5001)
            server.start()
            loop.start()

        self.server_thread = Thread(target=_run_loop)
        self.server_thread.start()

    # https://blog.bokeh.org/programmatic-bokeh-servers-9c8b0ea5d790
    def _update(self, source):
        if self.last_data_length is not None and self.last_data_length != len(self.plot_data):
            diff = len(self.plot_data) - self.last_data_length
            for i in range(diff):
                source.stream(self.plot_data[-(diff - i)])
        self.last_data_length = len(self.plot_data)

    def _make_bokeh_doc(self, doc, update):
        source = ColumnDataSource(self.plot_data[0])
        x_range = DataRange1d(follow='end', follow_interval=20000, range_padding=0)
        fig = figure(
            title="Data",
            x_axis_type='datetime',
            tools='',
            x_range=x_range)

        fig.line(source=source, x=TIME, y=DOWNLOAD_TASKS, color='red')
        fig.line(source=source, x=TIME, y=INDEX_TASKS, color='green')
        fig.line(source=source, x=TIME, y=DB_READS, color='blue')
        fig.line(source=source, x=TIME, y=DB_WRITES, color='yellow')
        fig.yaxis.minor_tick_line_color = None

        fig.add_tools(
            ResetTool(),
            PanTool(dimensions="width"),
            WheelZoomTool(dimensions="width")
        )
        doc.title = "Indexer State"
        doc.add_root(fig)
        doc.add_periodic_callback(functools.partial(update, source=source), 100)

