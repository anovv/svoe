# json files should be in ../../../../../helm/charts/local/grafana-dashboards/dashboards/ to be mounted to kube configmaps
# generate-dashboard -o path_above/svoe_data_feed_collector_stats.json svoe_data_feed_collectorq_stats.dashboard.py
import grafanalib.core as G

PROMETHEUS_DATA_SOURCE = 'Prometheus'
METRIC_NAME_LATENCY_COUNT = 'svoe_latency_ms_histogram_count'
METRIC_NAME_LATENCY_BUCKET = 'svoe_latency_ms_histogram_bucket'
METRIC_NAME_BLOCK_SIZE_GAUGE = 'svoe_data_size_kb_gauge'

# TODO figure out template per graph
template_list = [
    G.Template(
        default='l2_book',
        includeAll=True,
        multi=True,
        dataSource=PROMETHEUS_DATA_SOURCE,
        name='data_type',
        label='Data Type',
        query=f'label_values({METRIC_NAME_LATENCY_COUNT}, data_type)'
    ),
    G.Template(
        default='BINANCE',
        includeAll=True,
        multi=True,
        dataSource=PROMETHEUS_DATA_SOURCE,
        name='exchange',
        label='Exchange',
        query=f'label_values({METRIC_NAME_LATENCY_COUNT}, exchange)'
    ),
    G.Template(
        default='BTC-USDT',
        includeAll=True,
        multi=True,
        dataSource=PROMETHEUS_DATA_SOURCE,
        name='symbol',
        label='Symbol',
        query=f'label_values({METRIC_NAME_LATENCY_COUNT}, symbol)'
    ),
]


def _frequency_graph(title, operation, agg_window):
    return G.Graph(
        title=title,
        dataSource=PROMETHEUS_DATA_SOURCE,
        targets=[
            G.Target(
                expr=f'rate({METRIC_NAME_LATENCY_COUNT}{{operation=\'{operation}\', data_type=~\'$data_type\', exchange=~\'$exchange\', symbol=~\'$symbol\'}}[{agg_window}])',
            ),
        ],
        yAxes=G.single_y_axis(format=G.OPS_FORMAT),
        lineWidth=1,
    )

def _cached_block_size_graph():
    return G.Graph(
        title='Cached Block Size',
        dataSource=PROMETHEUS_DATA_SOURCE,
        targets=[
            G.Target(
                expr=f'{METRIC_NAME_BLOCK_SIZE_GAUGE}{{object=\'aggregator_cached_on_read\', data_type=~\'$data_type\', exchange=~\'$exchange\', symbol=~\'$symbol\'}} * 1024',
            ),
        ],
        yAxes=G.single_y_axis(format=G.BYTES_FORMAT),
        lineWidth=1,
    )


def _latency_graph(title, operation, agg_window):
    # TODO why is it rate here instead of raw bucket values??
    expr_template_lambda = \
        lambda quantile: f'histogram_quantile({quantile}, rate({METRIC_NAME_LATENCY_BUCKET}{{operation=\'{operation}\', data_type=~\'$data_type\', exchange=~\'$exchange\', symbol=~\'$symbol\'}}[{agg_window}]))'
    quantiles = ['0.95', '0.5']
    targets = list(map(lambda quantile: G.Target(expr=expr_template_lambda(quantile)), quantiles))
    return G.Graph(
        title=title,
        dataSource=PROMETHEUS_DATA_SOURCE,
        targets=targets,
        yAxes=G.single_y_axis(format=G.MILLISECONDS_FORMAT),
        lineWidth=1,
    )

# TODO total write times graphs
dashboard = G.Dashboard(
    title='Data Feed Aggregator Metrics',
    description='Latency, operations frequency and object sizes for aggregator',
    timezone='browser',
    templating=G.Templating(list=template_list),
    rows=[
        # cache reads row
        G.Row(panels=[
            _frequency_graph('Cache Reads Frequency (1m agg)', 'read', '1m'),
            _latency_graph('Cache Reads Latency (5m agg)', 'read', '5m')
        ]),
        # remote writes row
        G.Row(panels=[
            _frequency_graph('Remote Writes Frequency (1m agg)', 'write', '1m'),
            _latency_graph('Remote Writes Latency (5m agg)', 'write', '5m')
        ]),
        # block size row
        G.Row(panels=[
            _cached_block_size_graph()
        ])
    ]
).auto_panel_ids()

