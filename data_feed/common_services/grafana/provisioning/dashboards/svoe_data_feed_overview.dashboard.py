# json files should be in ../../../../../helm/charts/local/grafana-dashboards/dashboards/ to be mounted to kube configmaps
# generate-dashboard -o path_above/svoe_data_feed_overview.json svoe_data_feed_overview.dashboard.py
import grafanalib.core as G

DATA_FEED_NAMESPACE = 'data-feed'
PROMETHEUS_DATA_SOURCE = 'Prometheus'
# METRIC_NAME_LATENCY_COUNT = 'svoe_data_feed_collector_latency_s_histogram_count'
# METRIC_NAME_LATENCY_BUCKET = 'svoe_data_feed_collector_latency_s_histogram_bucket'
METRIC_NAME_CONN_HEALTH_GAUGE = 'svoe_data_feed_collector_conn_health_gauge'


def _total_conn_stat():
    # TODO add version label for case of duplicate data_type with different configs
    return G.Stat(
        title='Total number of connections (exchange+data_type+symbol)',
        dataSource=PROMETHEUS_DATA_SOURCE,
        targets=[
            G.Target(
                expr=f'count(group({METRIC_NAME_CONN_HEALTH_GAUGE}) by (exchange, data_type, symbol)) or on() vector(0)',
            ),
        ],
        reduceCalc='last',
    )


def _healthy_conn_stat():
    # TODO add version label for case of duplicate data_type with different configs
    return G.Stat(
        title='Total number of healthy connections (exchange+data_type+symbol)',
        dataSource=PROMETHEUS_DATA_SOURCE,
        targets=[
            G.Target(
                expr=f'count(group({METRIC_NAME_CONN_HEALTH_GAUGE} == 1) by (exchange, data_type, symbol)) or on() vector(0)',
            ),
        ],
        reduceCalc='last',
    )


# https://community.grafana.com/t/extract-labels-values-from-prometheus-metrics/2087/9
def _non_healthy_conn_table():
    return G.Table(
        title='Non-healthy connections',
        dataSource=PROMETHEUS_DATA_SOURCE,
        targets=[
            G.Target(
                expr=f'max({METRIC_NAME_CONN_HEALTH_GAUGE} != 1) by (exchange, data_type, symbol, pod, instance)',
                instant=True,
                format=G.TABLE_TARGET_FORMAT
            ),
        ],
    )


def _total_ss_count_stat():
    return G.Stat(
        title='Total number of statefulsets',
        dataSource=PROMETHEUS_DATA_SOURCE,
        targets=[
            G.Target(
                expr=f'count(group(kube_statefulset_created{{namespace=\'{DATA_FEED_NAMESPACE}\'}}) by (statefulset)) or on() vector(0)',
            ),
        ],
        reduceCalc='last',
    )


def _total_pod_count_stat():
    return G.Stat(
        title='Total number of pods',
        dataSource=PROMETHEUS_DATA_SOURCE,
        targets=[
            G.Target(
                expr=f'count(group(kube_pod_info{{namespace=\'{DATA_FEED_NAMESPACE}\'}}) by (pod)) or on() vector(0)',
            ),
        ],
        reduceCalc='last',
    )


def _running_pod_count_stat():
    return G.Stat(
        title='Number of running pods',
        dataSource=PROMETHEUS_DATA_SOURCE,
        targets=[
            G.Target(
                expr=f'count(group(kube_pod_status_phase{{namespace=\'{DATA_FEED_NAMESPACE}\', phase=\'Running\'}}) by (pod)) or on() vector(0)',
            ),
        ],
        reduceCalc='last',
    )


def _non_running_pod_table():
    return G.Table(
        title='Non running pods',
        dataSource=PROMETHEUS_DATA_SOURCE,
        targets=[
            G.Target(
                expr=f'max(kube_pod_status_phase{{namespace=\'{DATA_FEED_NAMESPACE}\', phase!=\'Running\'}}) by (pod, phase, instance)',
                instant=True,
                format=G.TABLE_TARGET_FORMAT
            ),
        ],
    )


def _non_ready_pod_table():
    return G.Table(
        title='Non ready pods',
        dataSource=PROMETHEUS_DATA_SOURCE,
        targets=[
            G.Target(
                expr=f'max(kube_pod_status_ready{{namespace=\'{DATA_FEED_NAMESPACE}\', condition!=\'true\'}}) by (pod, condition, instance)',
                instant=True,
                format=G.TABLE_TARGET_FORMAT
            ),
        ],
    )


dashboard = G.Dashboard(
    title='Data Feed Overview',
    description='Data Feed overview',
    timezone='browser',
    rows=[
        G.Row(panels=[_total_ss_count_stat(), _total_pod_count_stat(), _running_pod_count_stat()]),
        G.Row(panels=[_non_running_pod_table(), _non_ready_pod_table()]),
        G.Row(panels=[_total_conn_stat(), _healthy_conn_stat(), _non_healthy_conn_table()])
    ]
).auto_panel_ids()
