import functools
from threading import Thread
from time import time
from typing import Dict, List, Callable, Tuple, Optional, Union

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


GraphData = List[Union[List, Optional[int]]] # List with timestamped data point and last read data length

TIME = 'time'

# task events graph
GRAPH_NAME_TASK_EVENTS = 'GRAPH_NAME_TASK_EVENTS'
DOWNLOAD_TASKS_SCHEDULED = 'DOWNLOAD_TASKS_SCHEDULED'
DOWNLOAD_TASKS_STARTED = 'DOWNLOAD_TASKS_STARTED'
DOWNLOAD_TASKS_FINISHED = 'DOWNLOAD_TASKS_FINISHED'
INDEX_TASKS_SCHEDULED = 'INDEX_TASKS_SCHEDULED'
INDEX_TASKS_STARTED = 'INDEX_TASKS_STARTED'
INDEX_TASKS_FINISHED = 'INDEX_TASKS_FINISHED'
FILTER_BATCH = 'FILTER_BATCH'
WRITE_DB = 'WRITE_DB'


def _make_task_events_graph_data() -> GraphData:
    return [[{
        TIME: [time() * 1000],
        DOWNLOAD_TASKS_SCHEDULED: [0],
        DOWNLOAD_TASKS_STARTED: [0],
        DOWNLOAD_TASKS_FINISHED: [0],
        INDEX_TASKS_SCHEDULED: [0],
        INDEX_TASKS_STARTED: [0],
        INDEX_TASKS_FINISHED: [0],
        FILTER_BATCH: [0],
        WRITE_DB: [0]
    }], None]


def _make_task_events_graph_figure(source):
    fig = figure(title="Tasks Events", x_axis_type='datetime', tools='')

    for name in [DOWNLOAD_TASKS_SCHEDULED, DOWNLOAD_TASKS_STARTED, DOWNLOAD_TASKS_FINISHED, INDEX_TASKS_SCHEDULED, INDEX_TASKS_STARTED, INDEX_TASKS_FINISHED]:
        color = 'red' if 'DOWNLOAD' in name else 'green'
        line_dash = 'solid'
        if 'SCHEDULED' in name:
            line_dash = 'dotted'
        elif 'STARTED' in name:
            line_dash = 'dashed'
        legend_label = name

        fig.line(source=source, x=TIME, y=name, color=color, legend_label=legend_label, line_dash=line_dash)

    fig.line(source=source, x=TIME, y=FILTER_BATCH, color='blue', legend_label=FILTER_BATCH)
    fig.line(source=source, x=TIME, y=WRITE_DB, color='yellow', legend_label=WRITE_DB)
    fig.yaxis.minor_tick_line_color = None

    fig.add_tools(
        ResetTool(),
        PanTool(dimensions="width"),
        WheelZoomTool(dimensions="width")
    )

    fig.legend.location = 'top_left'
    fig.legend.label_text_font_size = '6pt'

    return fig


# task latencies graph
GRAPH_NAME_TASK_LATENCIES = 'GRAPH_NAME_TASK_LATENCIES'
DOWNLOAD_TASK_EXECUTION_TIME = 'DOWNLOAD_TASK_EXECUTION_TIME'
INDEX_TASK_EXECUTION_TIME = 'INDEX_TASK_EXECUTION_TIME'
FILTER_BATCH_EXECUTION_TIME = 'FILTER_BATCH_EXECUTION_TIME'
WRITE_DB_EXECUTION_TIME = 'WRITE_DB_EXECUTION_TIME'


def _make_task_latencies_graph_data() -> GraphData:
    return [[{
        TIME: [time() * 1000],
        DOWNLOAD_TASK_EXECUTION_TIME: [0],
        INDEX_TASK_EXECUTION_TIME: [0],
        FILTER_BATCH_EXECUTION_TIME: [0],
        WRITE_DB_EXECUTION_TIME: [0]
    }], None]


def _make_task_latencies_graph_figure(source):
    fig = figure(title="Tasks Latencies", x_axis_type='datetime', tools='')

    for name in [DOWNLOAD_TASK_EXECUTION_TIME, INDEX_TASK_EXECUTION_TIME, FILTER_BATCH_EXECUTION_TIME, WRITE_DB_EXECUTION_TIME]:
        color = None
        if 'DOWNLOAD' in name:
            color = 'red'
        elif 'INDEX' in name:
            color = 'green'
        elif 'FILTER' in name:
            color = 'blue'
        elif 'WRITE' in name:
            color = 'yellow'

        legend_label = name

        fig.line(source=source, x=TIME, y=name, color=color, legend_label=legend_label, line_dash='solid')

    fig.yaxis.minor_tick_line_color = None

    fig.add_tools(
        ResetTool(),
        PanTool(dimensions="width"),
        WheelZoomTool(dimensions="width")
    )

    fig.legend.location = 'top_left'
    fig.legend.label_text_font_size = '6pt'

    return fig

@ray.remote
class Stats:
    def __init__(self):
        self.graphs_data = {
            GRAPH_NAME_TASK_EVENTS: _make_task_events_graph_data(),
            GRAPH_NAME_TASK_LATENCIES: _make_task_latencies_graph_data()
        }

    def inc_counter(self, counter_name: str, increment: int = 1, graph_name: str = GRAPH_NAME_TASK_EVENTS):
        new_event = {}
        last_event = self.graphs_data[graph_name][0][-1]
        for _counter_name in last_event:
            if _counter_name == TIME:
                new_event[TIME] = [time() * 1000]
            elif _counter_name == counter_name:
                new_event[_counter_name] = [last_event[_counter_name][0] + increment]
            else:
                new_event[_counter_name] = [last_event[_counter_name][0]]
        self.graphs_data[graph_name][0].append(new_event)

    def set_values(self, kv: Dict[str, int], graph_name: str = GRAPH_NAME_TASK_LATENCIES):
        new_event = {}
        last_event = self.graphs_data[graph_name][0][-1]
        for _key_name in last_event:
            if _key_name == TIME:
                new_event[TIME] = [time() * 1000]
            elif _key_name in kv:
                new_event[_key_name] = [kv[_key_name]]
            else:
                new_event[_key_name] = [last_event[_key_name][0]]
        self.graphs_data[graph_name][0].append(new_event)


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
    def _update(self, sources):
        for graph_name in self.graphs_data:
            source = sources[graph_name]
            plot_data = self.graphs_data[graph_name][0]
            last_data_length = self.graphs_data[graph_name][1]
            if last_data_length is not None and last_data_length != len(plot_data):
                diff = len(plot_data) - last_data_length
                for i in range(diff):
                    source.stream(plot_data[-(diff - i)])

            # update last_data_length for this graph
            self.graphs_data[graph_name][1] = len(plot_data)

    def _make_bokeh_doc(self, doc, update):
        sources = {graph_name: ColumnDataSource(self.graphs_data[graph_name][0][0]) for graph_name in self.graphs_data}
        # x_range = DataRange1d(follow='end', follow_interval=20000, range_padding=0)
        fig = _make_task_events_graph_figure(sources[GRAPH_NAME_TASK_EVENTS])
        doc.title = "Indexer State"
        doc.add_root(fig)
        doc.add_periodic_callback(functools.partial(update, sources=sources), 100)

