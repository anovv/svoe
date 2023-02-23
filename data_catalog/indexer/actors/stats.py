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
            TIME: [time() * 1000],
            DOWNLOAD_TASKS: [1],
            INDEX_TASKS: [2],
            'download_queue_size': [3],
            'index_queue_size': [4],
            'store_queue_size': [5],
            DB_READS: [6],
            DB_WRITES: [7]
        }

    # def wait_and_update_counter(self, ref: ObjectRef, counter_name: str):
    #     ray.wait([ref])
    #     self.update_counter(counter_name)

    def inc_counter(self, counter_name: str):
        for _counter_name in self.state:
            if _counter_name == TIME:
                self.state[TIME].append(time() * 1000)
            elif _counter_name == counter_name:
                self.state[_counter_name].append(self.state[_counter_name][-1] + 1)
            else:
                self.state[_counter_name].append(self.state[_counter_name][-1])


    def poll_queues_states(self):
        pass

    def poll_cluster_state(self):
        pass

    # def _update_bokeh(self, source):
    #     # TODO lock on state ?
    #     # keep
    #     data = self.state.copy()

    # TODO this should be on a separate thread
    def run(self):
        def _run_loop():
            # start bokeh server
            apps = {'/': Application(FunctionHandler(functools.partial(self._make_bokeh_doc, update=self._update)))}
            # apps = {'/': Application(FunctionHandler(make_test_document))}
            loop = tornado.ioloop.IOLoop()
            server = Server(apps, io_loop=loop, port=5001)
            server.start()
            loop.start()

        self.server_thread = Thread(target=_run_loop)
        self.server_thread.start()

    # TODO this is buggy, fix this
    def _update(self, source, last_update_index_state):
        last_index = len(self.state[TIME]) - 1
        if last_index > last_update_index_state[0]:
            # stream diff
            diff = {k: v[last_update_index_state[0]:last_index] for k, v in self.state.items()}
            source.stream(diff)
            last_update_index_state[0] = last_index
            print(f'Diff len: {len(diff[TIME])}')

    def _make_bokeh_doc(self, doc, update):
        source = ColumnDataSource(self.state)
        x_range = DataRange1d(follow='end', follow_interval=20000, range_padding=0)
        fig = figure(
            title="Data",
            x_axis_type='datetime',
            tools='',
            # height=150,
            x_range=x_range,
            y_range=[-0.1, 20 + 0.1]) # TODO 100

        # indicates last pushed data, with each sequent update we only stream new data
        last_update_index_state = [len(self.state[TIME]) - 1]

        doc.add_periodic_callback(functools.partial(update, source=source, last_update_index_state=last_update_index_state), 100)

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

