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
from bokeh.layouts import row
from ray.types import ObjectRef

import ray

# for async wait/signaling see last comment https://github.com/ray-project/ray/issues/7229
# for streaming to Bokeh https://matthewrocklin.com/blog/work/2017/06/28/simple-bokeh-server
# for threaded updates https://stackoverflow.com/questions/55176868/asynchronous-streaming-to-embedded-bokeh-server

# counter names
# TODO enum
from tornado.ioloop import IOLoop


TIME = 'time'

DOWNLOAD_TASKS_SCHEDULED = 'download_tasks_scheduled'
DOWNLOAD_TASKS_STARTED = 'download_tasks_finished'
DOWNLOAD_TASKS_FINISHED = 'download_tasks_finished'
INDEX_TASKS_SCHEDULED = 'index_tasks_scheduled'
INDEX_TASKS_STARTED = 'index_tasks_started'
INDEX_TASKS_FINISHED = 'index_tasks_finished'

FILTER_BATCH = 'db_reads'
WRITE_DB = 'db_writes'


@ray.remote
class Stats:
    def __init__(self):
        self.tasks_plot_data = [{
            TIME: [time() * 1000],
            DOWNLOAD_TASKS_SCHEDULED: [0],
            DOWNLOAD_TASKS_STARTED: [0],
            DOWNLOAD_TASKS_FINISHED: [0],
            INDEX_TASKS_SCHEDULED: [0],
            INDEX_TASKS_STARTED: [0],
            INDEX_TASKS_FINISHED: [0],
            FILTER_BATCH: [0],
            WRITE_DB: [0]
        }]
        self.last_data_length = None

    def inc_counter(self, counter_name: str, increment: int = 1):
        new_event = {}
        last_event = self.tasks_plot_data[-1]
        for _counter_name in last_event:
            if _counter_name == TIME:
                new_event[TIME] = [time() * 1000]
            elif _counter_name == counter_name:
                new_event[_counter_name] = [last_event[_counter_name][0] + increment]
            else:
                new_event[_counter_name] = [last_event[_counter_name][0]]
        self.tasks_plot_data.append(new_event)


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
        if self.last_data_length is not None and self.last_data_length != len(self.tasks_plot_data):
            diff = len(self.tasks_plot_data) - self.last_data_length
            for i in range(diff):
                source.stream(self.tasks_plot_data[-(diff - i)])
        self.last_data_length = len(self.tasks_plot_data)

    def _make_bokeh_doc(self, doc, update):
        source = ColumnDataSource(self.tasks_plot_data[0])
        # x_range = DataRange1d(follow='end', follow_interval=20000, range_padding=0)
        fig = figure(title="Tasks", x_axis_type='datetime', tools='')

        fig.line(source=source, x=TIME, y=DOWNLOAD_TASKS_SCHEDULED, color='red', legend_label='Download Tasks Scheduled', line_dash='dotted')
        fig.line(source=source, x=TIME, y=DOWNLOAD_TASKS_STARTED, color='red', legend_label='Download Tasks Started', line_dash='dashed')
        fig.line(source=source, x=TIME, y=DOWNLOAD_TASKS_FINISHED, color='red', legend_label='Download Tasks Finished', line_dash='solid')

        fig.line(source=source, x=TIME, y=INDEX_TASKS_SCHEDULED, color='green', legend_label='Index Tasks Scheduled', line_dash='dotted')
        fig.line(source=source, x=TIME, y=INDEX_TASKS_STARTED, color='green', legend_label='Index Tasks Started', line_dash='dashed')
        fig.line(source=source, x=TIME, y=INDEX_TASKS_FINISHED, color='green', legend_label='Index Tasks Finished', line_dash='solid')

        fig.line(source=source, x=TIME, y=FILTER_BATCH, color='blue', legend_label='Filter Batch Tasks')
        fig.line(source=source, x=TIME, y=WRITE_DB, color='yellow', legend_label='Write DB Tasks')
        fig.yaxis.minor_tick_line_color = None

        fig.add_tools(
            ResetTool(),
            PanTool(dimensions="width"),
            WheelZoomTool(dimensions="width")
        )

        # p = row([fig])

        doc.title = "Indexer State"
        doc.add_root(fig)
        doc.add_periodic_callback(functools.partial(update, source=source), 100)

