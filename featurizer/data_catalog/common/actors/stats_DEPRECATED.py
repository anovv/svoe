import copy
import functools
import math
from threading import Thread
from time import time, sleep
from typing import Dict, List, Optional, Union

from bokeh.server.server import Server
import tornado
from tornado.ioloop import IOLoop
from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from bokeh.models import ColumnDataSource
from bokeh.layouts import row, column
from bokeh.plotting import figure
import ray.experimental.state.api as ray_state_api

from featurizer.data_catalog.common.utils.register import TASK_NAMES, EVENT_NAMES, EventType, get_event_name

import ray

# for async wait/signaling see last comment https://github.com/ray-project/ray/issues/7229
# for streaming to Bokeh https://matthewrocklin.com/blog/work/2017/06/28/simple-bokeh-server
# for threaded updates https://stackoverflow.com/questions/55176868/asynchronous-streaming-to-embedded-bokeh-server


COLORS = ['red', 'green', 'blue', 'yellow', 'lightblue', 'chocolate', 'gray', 'lime', 'orange', 'pink', 'lavender']

GraphData = List[Union[List, Optional[int]]] # List with timestamped data point and last read data length

TIME = 'time'
# LOAD_DF_TASK_NAME = ray_task_name(load_df)
GRAPH_NAME_TASK_EVENTS = 'GRAPH_NAME_TASK_EVENTS'

# task latencies graph
GRAPH_NAME_TASK_LATENCIES = 'GRAPH_NAME_TASK_LATENCIES'

GRAPH_NAME_DOWNLOAD_THROUGHPUT_MB = 'GRAPH_NAME_DOWNLOAD_THROUGHPUT_MB'
DOWNLOAD_THROUGHPUT_MB = 'DOWNLOAD_THROUGHPUT_MB'
GRAPH_NAME_DOWNLOAD_THROUGHPUT_NUM_FILES = 'GRAPH_NAME_DOWNLOAD_THROUGHPUT_NUM_FILES'
DOWNLOAD_THROUGHPUT_NUM_FILES = 'DOWNLOAD_THROUGHPUT_NUM_FILES'

GRAPH_NAME_CLUSTER_NUM_WORKERS = 'GRAPH_NAME_CLUSTER_NUM_WORKERS'
CLUSTER_NUM_WORKERS = 'CLUSTER_NUM_WORKERS'


# TODO use max_concurrency=n instead of threads
# @ray.remote(resources={'worker_size_small': 1, 'instance_on_demand': 1})
@ray.remote
class Stats:
    def __init__(self):
        self.task_events = {task_name: [] for task_name in TASK_NAMES}
        self.graphs_data = {
            GRAPH_NAME_TASK_EVENTS: self._make_graph_data(EVENT_NAMES),
            GRAPH_NAME_TASK_LATENCIES: self._make_graph_data(TASK_NAMES),
            GRAPH_NAME_DOWNLOAD_THROUGHPUT_NUM_FILES: self._make_graph_data([DOWNLOAD_THROUGHPUT_NUM_FILES]),
            GRAPH_NAME_DOWNLOAD_THROUGHPUT_MB: self._make_graph_data([DOWNLOAD_THROUGHPUT_MB]),
            GRAPH_NAME_CLUSTER_NUM_WORKERS: self._make_graph_data([CLUSTER_NUM_WORKERS]),
        }

    def _make_graph_data(self, keys) -> GraphData:
        first = {TIME: [time() * 1000.0]}
        first.update(dict(zip(keys, [[0] for _ in keys])))
        return [[first], None]

    def send_events(self, task_name: str, events: List[Dict]):
        self.task_events[task_name].extend(events)

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

    # def _calc_metrics_loop(self):
    #     sleep(1)

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

                    # if call ray_task_name(load_df) directly here, it won't serialize
                    # load_df_task_name = LOAD_DF_TASK_NAME
                    load_df_task_name = 'load_df'
                    for event in self.task_events[load_df_task_name]:
                        if event['event_name'] == get_event_name(load_df_task_name, EventType.FINISHED) \
                                and now - window_s <= event['timestamp'] <= now:
                            # find corresponding 'load_df_started' event for this task_id
                            started_event = None
                            # TODO this can be optimized to avoid nested loop
                            for s_event in self.task_events[load_df_task_name]:
                                if s_event['task_id'] == event['task_id'] and s_event['event_name'] == get_event_name(load_df_task_name, EventType.STARTED):
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
                    # TODO try except this
                    workers = ray_state_api.list_workers(address='auto', limit=100, timeout=30, raise_on_missing_output=True)
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
        fig_events = self._make_task_events_graph_figure(sources[GRAPH_NAME_TASK_EVENTS])
        fig_latencies = self._make_task_latencies_graph_figure(sources[GRAPH_NAME_TASK_LATENCIES])

        fig_throughput_mb = self._make_single_line_graph_figure(sources[GRAPH_NAME_DOWNLOAD_THROUGHPUT_MB], 'Download Throughput (Mb/s)', DOWNLOAD_THROUGHPUT_MB)
        fig_throughput_num_files = self._make_single_line_graph_figure(sources[GRAPH_NAME_DOWNLOAD_THROUGHPUT_NUM_FILES], 'Download Throughput (Files/s)', DOWNLOAD_THROUGHPUT_NUM_FILES)

        fig_cluster_num_workers = self._make_single_line_graph_figure(sources[GRAPH_NAME_CLUSTER_NUM_WORKERS], 'Cluster Worker Actors (count)', CLUSTER_NUM_WORKERS)

        c1 = column(fig_events, fig_cluster_num_workers)
        c2 = column(fig_latencies, fig_throughput_mb, fig_throughput_num_files)
        r = row(c1, c2)
        doc.title = "Indexer Stats"
        doc.add_root(r)
        doc.add_periodic_callback(functools.partial(update, sources=sources), 100)

    def _make_task_events_graph_figure(self, source):
        fig = figure(title="Tasks Events (count)", x_axis_type='datetime', tools='')
        color_index = 0
        color_per_task = {}
        for name in EVENT_NAMES:
            # same color for same task
            task_name = None
            for t_name in TASK_NAMES:
                if t_name in name:
                    task_name = t_name
                    break

            if task_name in color_per_task:
                color = color_per_task[task_name]
            else:
                color = COLORS[color_index % len(COLORS)]
                color_per_task[task_name] = color
                color_index += 1

            line_dash = 'solid'
            if EventType.SCHEDULED.value in name:
                line_dash = 'dotted'
            elif EventType.STARTED.value in name:
                line_dash = 'dashed'
            legend_label = name

            fig.line(source=source, x=TIME, y=name, color=color, legend_label=legend_label, line_dash=line_dash)

        fig.yaxis.minor_tick_line_color = None

        fig.legend.location = 'top_left'
        fig.legend.label_text_font_size = '6pt'

        return fig

    def _make_single_line_graph_figure(self, source, title, y_name):
        fig = figure(title=title, x_axis_type='datetime', tools='')

        # TODO for running ranges
        # x_range = DataRange1d(follow='end', follow_interval=20000, range_padding=0)
        fig.line(source=source, x=TIME, y=y_name, color='red')
        fig.yaxis.minor_tick_line_color = None

        return fig

    def _make_task_latencies_graph_figure(self, source):
        fig = figure(title="Normalized Tasks Latencies (seconds per kb per task)", x_axis_type='datetime', tools='')

        # TODO for running ranges
        # x_range = DataRange1d(follow='end', follow_interval=20000, range_padding=0)
        for i in range(len(TASK_NAMES)):
            name = TASK_NAMES[i]
            color = COLORS[i % len(COLORS)]

            legend_label = name

            fig.line(source=source, x=TIME, y=name, color=color, legend_label=legend_label, line_dash='solid')

        fig.yaxis.minor_tick_line_color = None

        fig.legend.location = 'top_left'
        fig.legend.label_text_font_size = '6pt'

        return fig
