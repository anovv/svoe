import asyncio
import aiohttp

from perf.defines import PROM, RUN_ESTIMATION_FOR, DATA_FEED_CONTAINER, REDIS_CONTAINER, REDIS_EXPORTER_CONTAINER


def fetch_metrics(pod_name, payload_config):
    # this will be called inside pool executor, each in separate thread
    # hence we need to create a new loop instance for each thread
    loop = asyncio.new_event_loop()
    res = loop.run_until_complete(_fetch_metrics_async(pod_name, payload_config))
    loop.close()
    return res


async def _fetch_metric_async(metric_type, metric_name, metric_query, session):
    retries = 10
    params = {
        'query': metric_query,
    }
    metric_value = None
    error = None
    count = 0
    while count < retries:
        count += 1
        try:
            error = None
            async with session.get(PROM + '/api/v1/query', params=params) as response:
                resp = await response.json()
                status = resp['status']
                if status != 'success':
                    error = resp['error']
                else:
                    metric_value = resp['data']['result'][0]['value'][1]
        except Exception as e:
            error = e.__class__.__name__ + ': ' + str(e)

        if error:
            await asyncio.sleep(1)
        else:
            break

    return metric_type, metric_name, metric_value, error


async def _fetch_metrics_async(pod_name, payload_config):
    health_metrics = _get_data_feed_health_metrics_queries(pod_name, payload_config)
    perf_metrics = _get_perf_kube_metrics_server_queries(pod_name)
    metric_queries = {**health_metrics, **perf_metrics}
    tasks = []
    session = aiohttp.ClientSession()
    for metric_name in metric_queries:
        tasks.append(asyncio.ensure_future(_fetch_metric_async(
            'health' if metric_name in health_metrics else 'perf',
            metric_name,
            metric_queries[metric_name],
            session
        )))
    res = await asyncio.gather(*tasks)
    await session.close()
    return res


def _get_data_feed_health_metrics_queries(pod_name, payload_config):
    duration = f'[{RUN_ESTIMATION_FOR}s]'
    duration_subquery = f'[{RUN_ESTIMATION_FOR}s:]'
    metrics = {}
    for exchange in payload_config:
        # TODO decide channel/data_type naming
        for data_type in payload_config[exchange]:
            for symbol in payload_config[exchange][data_type]:
                metrics.update({
                    # TODO add aggregation over other labels ?
                    # TODO ',' or ';' separator instead of '_'
                    f'health_absent_{data_type}_{symbol}':
                        f'avg_over_time((max(absent(svoe_data_feed_collector_conn_health_gauge{{exchange="{exchange}", symbol="{symbol}", data_type="{data_type}"}})) or vector(0)){duration_subquery})',
                    f'health_avg_{data_type}_{symbol}': f'avg_over_time(svoe_data_feed_collector_conn_health_gauge{{exchange="{exchange}", symbol="{symbol}", data_type="{data_type}"}}{duration})'
                })

    return metrics


def _get_perf_kube_metrics_server_queries(pod_name):
    # https://github.com/olxbr/metrics-server-exporter to export metrics-server to prometheus
    duration = f'[{RUN_ESTIMATION_FOR}s]'
    duration_subquery = f'[{RUN_ESTIMATION_FOR}s:]'
    metrics = {}
    for container_name in [DATA_FEED_CONTAINER, REDIS_CONTAINER, REDIS_EXPORTER_CONTAINER]:
        # TODO ',' or ';' separator instead of '_'
        metrics.update({
            # mem
            f'kube_metrics_server_mem_absent_{container_name}':
                f'avg_over_time((max(absent(kube_metrics_server_pods_mem{{pod_name="{pod_name}", pod_container_name="{container_name}"}})) or vector(0)){duration_subquery})',
            f'kube_metrics_server_mem_avg_{container_name}': f'avg_over_time(kube_metrics_server_pods_mem{{pod_name="{pod_name}", pod_container_name="{container_name}"}}{duration})',
            f'kube_metrics_server_mem_max_{container_name}': f'max_over_time(kube_metrics_server_pods_mem{{pod_name="{pod_name}", pod_container_name="{container_name}"}}{duration})',
            f'kube_metrics_server_mem_min_{container_name}': f'min_over_time(kube_metrics_server_pods_mem{{pod_name="{pod_name}", pod_container_name="{container_name}"}}{duration})',
            f'kube_metrics_server_mem_095_{container_name}': f'quantile_over_time(0.95, kube_metrics_server_pods_mem{{pod_name="{pod_name}", pod_container_name="{container_name}"}}{duration})',

            # cpu
            f'kube_metrics_server_cpu_absent_{container_name}':
                f'avg_over_time((max(absent(kube_metrics_server_pods_cpu{{pod_name="{pod_name}", pod_container_name="{container_name}"}})) or vector(0)){duration_subquery})',
            f'kube_metrics_server_cpu_avg_{container_name}': f'avg_over_time(kube_metrics_server_pods_cpu{{pod_name="{pod_name}", pod_container_name="{container_name}"}}{duration})',
            f'kube_metrics_server_cpu_max_{container_name}': f'max_over_time(kube_metrics_server_pods_cpu{{pod_name="{pod_name}", pod_container_name="{container_name}"}}{duration})',
            f'kube_metrics_server_cpu_min_{container_name}': f'min_over_time(kube_metrics_server_pods_cpu{{pod_name="{pod_name}", pod_container_name="{container_name}"}}{duration})',
            f'kube_metrics_server_cpu_095_{container_name}': f'quantile_over_time(0.95, kube_metrics_server_pods_cpu{{pod_name="{pod_name}", pod_container_name="{container_name}"}}{duration})',
        })

    return metrics


# TODO finish this
def _get_cadvisor_metrics(pod_name):
    duration = f'[{RUN_ESTIMATION_FOR}s]'
    duration_subquery = f'[{RUN_ESTIMATION_FOR}s:]'
    metrics = {}
    for container_name in [DATA_FEED_CONTAINER, REDIS_CONTAINER, REDIS_EXPORTER_CONTAINER]:
        # TODO ',' or ';' separator instead of '_'
        metrics.update({
            # TODO explore relevant metrics:
            # network
            # container_network_transmit_bytes_total
            # container_network_transmit_errors_total
            # container_network_receive_bytes_total
            # container_network_receive_errors_total

            # TODO https://www.metricfire.com/blog/top-10-cadvisor-metrics-for-prometheus/
            # https://prometheus.io/docs/guides/cadvisor/
            # https://www.cloudforecast.io/blog/cadvisor-and-kubernetes-monitoring-guide/
            # memory

            # cpu

            # mem
            f'mem_absent_{container_name}':
                f'avg_over_time((max(absent(kube_metrics_server_pods_mem{{pod_name="{pod_name}", pod_container_name="{container_name}"}})) or vector(0)){duration_subquery})',
            f'mem_avg_{container_name}': f'avg_over_time(kube_metrics_server_pods_mem{{pod_name="{pod_name}", pod_container_name="{container_name}"}}{duration})',
            f'mem_max_{container_name}': f'max_over_time(kube_metrics_server_pods_mem{{pod_name="{pod_name}", pod_container_name="{container_name}"}}{duration})',
            f'mem_min_{container_name}': f'min_over_time(kube_metrics_server_pods_mem{{pod_name="{pod_name}", pod_container_name="{container_name}"}}{duration})',
            f'mem_095_{container_name}': f'quantile_over_time(0.95, kube_metrics_server_pods_mem{{pod_name="{pod_name}", pod_container_name="{container_name}"}}{duration})',
        })

    return metrics
