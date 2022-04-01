# generate-dashboard -o svoe_data_feed_aggregator_stats.json svoe_data_feed_aggregator_stats.dashboard.py
import grafanalib.core as G

PROMETHEUS_DATA_SOURCE = 'Prometheus'
METRIC_NAME_LATENCY_COUNT = 'svoe_latency_ms_histogram_count'
METRIC_NAME_LATENCY_BUCKET = 'svoe_latency_ms_histogram_bucket'

# TODO figure out template per graph
template_list = [
    G.Template(
        default='',
        includeAll=True,
        multi=True,
        dataSource=PROMETHEUS_DATA_SOURCE,
        name='data_type',
        label='Data Type',
        query=f'label_values({METRIC_NAME_LATENCY_COUNT}, data_type)'
    ),
    G.Template(
        default='',
        includeAll=True,
        multi=True,
        dataSource=PROMETHEUS_DATA_SOURCE,
        name='exchange',
        label='Exchange',
        query=f'label_values({METRIC_NAME_LATENCY_COUNT}, exchange)'
    ),
    G.Template(
        default='',
        includeAll=True,
        multi=True,
        dataSource=PROMETHEUS_DATA_SOURCE,
        name='symbol',
        label='Symbol',
        query=f'label_values({METRIC_NAME_LATENCY_COUNT}, symbol)'
    ),
]


def _frequency_graph(title, operation):
    return G.Graph(
        title=title,
        dataSource=PROMETHEUS_DATA_SOURCE,
        targets=[
            G.Target(
                expr=f'rate({METRIC_NAME_LATENCY_COUNT}{{operation=\'{operation}\', data_type=~\'$data_type\', exchange=~\'$exchange\', symbol=~\'$symbol\'}}[1m])',
            ),
        ],
        yAxes=G.single_y_axis(format=G.OPS_FORMAT),
        lineWidth=1,
    )

def _latency_graph(title, operation):
    return G.Graph(
        title=title,
        dataSource=PROMETHEUS_DATA_SOURCE,
        targets=[
            # TODO add labels with percentile names
            G.Target(
                expr=f'histogram_quantile(0.95, rate({METRIC_NAME_LATENCY_BUCKET}{{operation=\'{operation}\', data_type=~\'$data_type\', exchange=~\'$exchange\', symbol=~\'$symbol\'}}[5m]))'
            ),
            G.Target(
                expr=f'histogram_quantile(0.5, rate({METRIC_NAME_LATENCY_BUCKET}{{operation=~\'{operation}\', data_type=~\'$data_type\', exchange=~\'$exchange\', symbol=~\'$symbol\'}}[5m]))'
            ),
        ],
        yAxes=G.single_y_axis(format=G.MILLISECONDS_FORMAT),
        lineWidth=1,
    )



dashboard = G.Dashboard(
    title='Data Feed Aggregator Metrics',
    description='Latency, operations frequency and object sizes for aggregator',
    timezone='browser',
    templating=G.Templating(list=template_list),
    rows=[
        # cache reads row
        G.Row(panels=[
            _frequency_graph('Cache Reads Frequency', 'read'),
            _latency_graph('Cache Reads Latency', 'read')
        ]),
        # remote write row
        G.Row(panels=[
            _frequency_graph('Remote Writes Frequency', 'write'),
            _latency_graph('Remote Writes Latency', 'write')
        ]),
    ]
).auto_panel_ids()

