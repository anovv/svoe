# json files should be in ../../../../../helm/charts/local/grafana-dashboards/dashboards/ to be mounted to kube configmaps
# generate-dashboard -o path_above/svoe_data_feed_overview.json svoe_data_feed_overview.dashboard.py
import grafanalib.core as G

PROMETHEUS_DATA_SOURCE = 'Prometheus'
METRIC_NAME_LATENCY_COUNT = 'svoe_data_feed_collector_latency_s_histogram_count'
METRIC_NAME_LATENCY_BUCKET = 'svoe_data_feed_collector_latency_s_histogram_bucket'
METRIC_NAME_CONN_HEALTH_GAUGE = 'svoe_data_feed_collector_conn_health_gauge'

# https://community.grafana.com/t/extract-labels-values-from-prometheus-metrics/2087/9
def _non_healthy_table():
    return G.Table(
        title='Non-healthy channels',
        dataSource=PROMETHEUS_DATA_SOURCE,
        targets=[
            G.Target(
                expr='max(kube_node_info) by (node, kernel_version, os_image)',
                instant=True,
                format=G.TABLE_TARGET_FORMAT
            ),
        ],
        # columns=['Kernel Version', 'Node', 'OS Image']
    )

dashboard = G.Dashboard(
    title='Data Feed Overview',
    description='Data Feed overview',
    timezone='browser',
    rows=[
        G.Row(panels=[
            _non_healthy_table()
        ])
    ]
).auto_panel_ids()

