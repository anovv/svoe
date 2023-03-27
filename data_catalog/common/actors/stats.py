import copy
import functools
import math
from threading import Thread
from time import time, sleep
from typing import Dict, List, Optional, Union

import tornado
from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from bokeh.server.server import Server
from bokeh.models import ColumnDataSource, ResetTool, PanTool, WheelZoomTool
from bokeh.plotting import figure
from bokeh.layouts import row, column
from ray.experimental.state.api import list_workers

from data_catalog.common.utils.register import TASK_NAMES, EVENT_NAMES, EventType, get_event_name, ray_task_name
from data_catalog.common.tasks.tasks import load_df, index_df, write_batch, filter_existing

import ray

# for async wait/signaling see last comment https://github.com/ray-project/ray/issues/7229
# for streaming to Bokeh https://matthewrocklin.com/blog/work/2017/06/28/simple-bokeh-server
# for threaded updates https://stackoverflow.com/questions/55176868/asynchronous-streaming-to-embedded-bokeh-server

from tornado.ioloop import IOLoop

GraphData = List[Union[List, Optional[int]]] # List with timestamped data point and last read data length

def _make_graph_data(keys) -> GraphData:
    first = {TIME: [time() * 1000.0]}
    first.update(dict(zip(keys, [[0] for _ in keys])))
    return [[first], None]

TIME = 'time'

GRAPH_NAME_TASK_EVENTS = 'GRAPH_NAME_TASK_EVENTS'


def _make_task_events_graph_figure(source):
    fig = figure(title="Tasks Events (count)", x_axis_type='datetime', tools='')
    for name in EVENT_NAMES:
        # TODO simplify this
        if ray_task_name(load_df) in name:
            color = 'red'
        elif ray_task_name(index_df) in name:
            color = 'green'
        elif ray_task_name(filter_existing) in name:
            color = 'blue'
        elif ray_task_name(write_batch) in name:
            color = 'yellow'

        line_dash = 'solid'
        if EventType.SCHEDULED.value in name:
            line_dash = 'dotted'
        elif EventType.STARTED.value in name:
            line_dash = 'dashed'
        legend_label = name

        fig.line(source=source, x=TIME, y=name, color=color, legend_label=legend_label, line_dash=line_dash)

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


def _make_task_latencies_graph_figure(source):
    fig = figure(title="Normalized Tasks Latencies (seconds per kb per task)", x_axis_type='datetime', tools='')

    # TODO for running ranges
    # x_range = DataRange1d(follow='end', follow_interval=20000, range_padding=0)
    for name in TASK_NAMES:
        # TODO simplify this
        color = None
        if ray_task_name(load_df) in name:
            color = 'red'
        elif ray_task_name(index_df) in name:
            color = 'green'
        elif ray_task_name(filter_existing) in name:
            color = 'blue'
        elif ray_task_name(write_batch) in name:
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


GRAPH_NAME_DOWNLOAD_THROUGHPUT_MB = 'GRAPH_NAME_DOWNLOAD_THROUGHPUT_MB'
DOWNLOAD_THROUGHPUT_MB = 'DOWNLOAD_THROUGHPUT_MB'
GRAPH_NAME_DOWNLOAD_THROUGHPUT_NUM_FILES = 'GRAPH_NAME_DOWNLOAD_THROUGHPUT_NUM_FILES'
DOWNLOAD_THROUGHPUT_NUM_FILES = 'DOWNLOAD_THROUGHPUT_NUM_FILES'


def _make_single_line_graph_figure(source, title, y_name):
    fig = figure(title=title, x_axis_type='datetime', tools='')

    # TODO for running ranges
    # x_range = DataRange1d(follow='end', follow_interval=20000, range_padding=0)
    fig.line(source=source, x=TIME, y=y_name, color='red')
    fig.yaxis.minor_tick_line_color = None
    fig.add_tools(
        ResetTool(),
        PanTool(dimensions="width"),
        WheelZoomTool(dimensions="width")
    )
    # fig.legend.location = 'top_left'
    # fig.legend.label_text_font_size = '6pt'

    return fig


GRAPH_NAME_CLUSTER_NUM_WORKERS = 'GRAPH_NAME_CLUSTER_NUM_WORKERS'
CLUSTER_NUM_WORKERS = 'CLUSTER_NUM_WORKERS'


@ray.remote
class Stats:
    def __init__(self):
        self.task_events = {task_name : [] for task_name in TASK_NAMES}
        self.graphs_data = {
            GRAPH_NAME_TASK_EVENTS: _make_graph_data(EVENT_NAMES),
            GRAPH_NAME_TASK_LATENCIES: _make_graph_data(TASK_NAMES),
            GRAPH_NAME_DOWNLOAD_THROUGHPUT_NUM_FILES: _make_graph_data([DOWNLOAD_THROUGHPUT_NUM_FILES]),
            GRAPH_NAME_DOWNLOAD_THROUGHPUT_MB: _make_graph_data([DOWNLOAD_THROUGHPUT_MB]),
            GRAPH_NAME_CLUSTER_NUM_WORKERS: _make_graph_data([CLUSTER_NUM_WORKERS]),
        }

    def event(self, task_name: str, event: Dict):
        self.task_events[task_name].append(event)

    def events(self, task_name: str, events: List[Dict]):
        self.task_events[task_name].extend(events)

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

        # TODO use asyncio?
        self.server_thread = Thread(target=_run_loop)
        self.server_thread.start()
        self.calc_metrics_thread = Thread(target=self._calc_metrics_loop)
        self.calc_metrics_thread.start()

    # https://blog.bokeh.org/programmatic-bokeh-servers-9c8b0ea5d790
    # https://github.com/bokeh/bokeh/blob/3.0.3/examples/server/app/ohlc/main.py
    # streaming example
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


    def _calc_metrics_loop(self):
        # TODO make proper flag
        while True:
            for graph_name in self.graphs_data:
                # TODO abstract it away on per-graph basis
                if graph_name == GRAPH_NAME_TASK_EVENTS:
                    now = time()
                    new_append = copy.deepcopy(self.graphs_data[graph_name][0][-1])

                    # plot data stores TIME is seconds
                    last_update_ts = new_append[TIME][0]/1000.0
                    new_append[TIME] = [now * 1000.0]

                    has_changed = False
                    for task_name in TASK_NAMES:
                        for event in self.task_events[task_name]:
                            if event['timestamp'] < last_update_ts:
                                continue
                            has_changed = True
                            event_name = event['event_name']
                            new_append[event_name][0] += 1
                    if has_changed:
                        self.graphs_data[graph_name][0].append(new_append)
                    continue
                if graph_name == GRAPH_NAME_TASK_LATENCIES:
                    now = time()
                    new_append = copy.deepcopy(self.graphs_data[graph_name][0][-1])

                    # plot data stores TIME is seconds
                    last_update_ts = new_append[TIME][0]/1000.0
                    new_append[TIME] = [now * 1000.0]
                    has_changed = False
                    for task_name in TASK_NAMES:
                        for event in self.task_events[task_name]:
                            if event['timestamp'] < last_update_ts:
                                continue
                            if 'latency' in event:
                                has_changed = True
                                latency = event['latency']
                                if 'size_kb' in event:
                                    # normalize
                                    latency /= float(event['size_kb'])
                                new_append[task_name][0] = latency
                    if has_changed:
                        self.graphs_data[graph_name][0].append(new_append)
                    continue

                if graph_name == GRAPH_NAME_DOWNLOAD_THROUGHPUT_MB or graph_name == GRAPH_NAME_DOWNLOAD_THROUGHPUT_NUM_FILES:
                    use_num_files = graph_name == GRAPH_NAME_DOWNLOAD_THROUGHPUT_NUM_FILES

                    # TODO const this
                    window_s = 60.0
                    now = time()
                    new_append = copy.deepcopy(self.graphs_data[graph_name][0][-1])

                    # plot data stores TIME is seconds
                    new_append[TIME] = [now * 1000.0]
                    size_kb = 0
                    num_files = 0
                    for event in self.task_events[ray_task_name(load_df)]:
                        if event['event_name'] == get_event_name(ray_task_name(load_df), EventType.FINISHED) and event['timestamp'] <= now and event['timestamp'] >= now - window_s:

                            # find corresponding 'load_df_started' event for this task_id
                            started_event = None
                            # TODO this can be optimized to avoid nested loop
                            for s_event in self.task_events[ray_task_name(load_df)]:
                                if s_event['task_id'] == event['task_id'] and s_event['event_name'] == get_event_name(ray_task_name(load_df), EventType.STARTED):
                                    started_event = s_event
                            if started_event is None:
                                continue
                            # two cases:
                            # 1. if start event is inside the window, we simply add it to total size
                            # 2. is it's outside, we add size proportional to what is inside the window
                            factor = 1 # default first case
                            if started_event['timestamp'] < now - window_s:
                                # second case
                                factor = window_s/(event['timestamp'] - started_event['timestamp'])
                            size_kb += factor * event['size_kb']
                            num_files += factor
                    if use_num_files:
                        val = num_files/window_s
                        # compare floats
                        has_changed = not math.isclose(new_append[DOWNLOAD_THROUGHPUT_NUM_FILES][0], val)
                        new_append[DOWNLOAD_THROUGHPUT_NUM_FILES][0] = val
                    else:
                        val = (size_kb/1024.0)/window_s
                        # compare floats
                        has_changed = not math.isclose(new_append[DOWNLOAD_THROUGHPUT_MB][0], val)
                        new_append[DOWNLOAD_THROUGHPUT_MB][0] = val

                    if has_changed:
                        self.graphs_data[graph_name][0].append(new_append)
                    continue

                if graph_name == GRAPH_NAME_CLUSTER_NUM_WORKERS:
                    # TODO try catch this
                    workers = list_workers(address='auto', limit=100, timeout=30, raise_on_missing_output=True)
                    num_alive_workers = 0
                    for worker_state in workers:
                        # TODO add dead worker count
                        if worker_state['worker_type'] == 'WORKER' and worker_state['is_alive']:
                            num_alive_workers += 1

                    now = time()
                    new_append = copy.deepcopy(self.graphs_data[graph_name][0][-1])
                    new_append[TIME] = [now * 1000.0]
                    new_append[CLUSTER_NUM_WORKERS] = [num_alive_workers]
                    self.graphs_data[graph_name][0].append(new_append)
                    continue

            sleep(0.1)
            # TODO clean up stale data (both task_events and graph_data) to avoid OOM

    def _make_bokeh_doc(self, doc, update):
        # TODO add rollover to ColumnDataSource to avoid OOM
        sources = {graph_name: ColumnDataSource(self.graphs_data[graph_name][0][0]) for graph_name in self.graphs_data}
        fig_events = _make_task_events_graph_figure(sources[GRAPH_NAME_TASK_EVENTS])
        fig_latencies = _make_task_latencies_graph_figure(sources[GRAPH_NAME_TASK_LATENCIES])

        fig_throughput_mb = _make_single_line_graph_figure(sources[GRAPH_NAME_DOWNLOAD_THROUGHPUT_MB], 'Download Throughput (Mb/s)', DOWNLOAD_THROUGHPUT_MB)
        fig_throughput_num_files = _make_single_line_graph_figure(sources[GRAPH_NAME_DOWNLOAD_THROUGHPUT_NUM_FILES], 'Download Throughput (Files/s)', DOWNLOAD_THROUGHPUT_NUM_FILES)

        fig_cluster_num_workers = _make_single_line_graph_figure(sources[GRAPH_NAME_CLUSTER_NUM_WORKERS], 'Cluster Worker Actors (count)', CLUSTER_NUM_WORKERS)

        c1 = column(fig_events, fig_cluster_num_workers)
        c2 = column(fig_latencies, fig_throughput_mb, fig_throughput_num_files)
        r = row(c1, c2)
        doc.title = "Indexer Stats"
        doc.add_root(r)
        doc.add_periodic_callback(functools.partial(update, sources=sources), 100)
