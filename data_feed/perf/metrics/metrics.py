import asyncio
import aiohttp
import random

from perf.defines import PROM, RUN_ESTIMATION_FOR, DATA_FEED_CONTAINER, REDIS_CONTAINER, REDIS_EXPORTER_CONTAINER
from perf.utils import nested_set


class AggregateFunction:
    ABSENT = 'absent'
    AVG = 'avg'
    MAX = 'max'
    MIN = 'min'
    P95 = 'p95'
    INC = 'inc'

    query_functions = {
        ABSENT: lambda metric, duration_s: f'avg_over_time((max(absent({metric})) or vector(0))[{duration_s}s:])',
        AVG: lambda metric, duration_s: f'avg_over_time({metric}[{duration_s}s])',
        MAX: lambda metric, duration_s: f'max_over_time({metric}[{duration_s}s])',
        MIN: lambda metric, duration_s: f'min_over_time({metric}[{duration_s}s])',
        P95: lambda metric, duration_s: f'quantile_over_time(0.95, {metric}[{duration_s}s])',
    }


class Metrics:
    # data feed health
    DATA_FEED_HEALTH = 'df_health'
    df_health_metrics = {
        DATA_FEED_HEALTH: lambda exchange, data_type, symbol: f'svoe_data_feed_collector_conn_health_gauge{{exchange="{exchange}", symbol="{symbol}", data_type="{data_type}"}}'
    }

    # exported by metrics-server-exporter
    MS_MEMORY = 'metrics_server_mem'
    MS_CPU = 'metrics_server_cpu'
    ms_metrics = {
        MS_MEMORY: lambda pod, container: f'kube_metrics_server_pods_mem{{pod_name="{pod}", pod_container_name="{container}"}}',
        MS_CPU: lambda pod, container: f'kube_metrics_server_pods_cpu{{pod_name="{pod}", pod_container_name="{container}"}}',
    }

    # TODO add cadvisor metrics


def fetch_metrics(pod_name, payload_config):
    # this will be called inside pool executor, each in separate thread
    # hence we need to create a new loop instance for each thread
    loop = asyncio.new_event_loop()
    res = loop.run_until_complete(_fetch_metrics_async(pod_name, payload_config))
    loop.close()
    return res


async def _fetch_metric_async(res, metric_query, location_keys, session):
    retries = 10
    retry_timeout_range = (1, 1) # randomly select retry timeout for uniform distribution
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
            await asyncio.sleep(random.randint(retry_timeout_range[0], retry_timeout_range[1]))
        else:
            break

    nested_set(res, location_keys, (metric_value, error))


async def _fetch_metrics_async(pod_name, payload_config):
    health_metrics = _get_data_feed_health_metrics_queries(pod_name, payload_config)
    perf_metrics = _get_perf_kube_metrics_server_queries(pod_name)
    metric_queries = {**health_metrics, **perf_metrics}
    tasks = []
    res = {}
    session = aiohttp.ClientSession()
    for metric_query in metric_queries:
        location_keys = metric_queries[metric_query]
        tasks.append(asyncio.ensure_future(_fetch_metric_async(
            res,
            metric_query,
            location_keys,
            session
        )))
    await asyncio.gather(*tasks)
    await session.close()
    return res


def _get_data_feed_health_metrics_queries(pod_name, payload_config):
    metrics = {}
    for exchange in payload_config:
        # TODO decide channel/data_type naming
        for data_type in payload_config[exchange]:
            for symbol in payload_config[exchange][data_type]:
                metric_health = Metrics.df_health_metrics[Metrics.DATA_FEED_HEALTH](exchange, data_type, symbol)
                for agg in [AggregateFunction.ABSENT, AggregateFunction.AVG]:
                    metrics[AggregateFunction.query_functions[agg](metric_health, RUN_ESTIMATION_FOR)] = [Metrics.DATA_FEED_HEALTH, data_type, symbol, agg]

    return metrics


def _get_perf_kube_metrics_server_queries(pod_name):
    # https://github.com/olxbr/metrics-server-exporter to export metrics-server to prometheus
    metrics = {}
    for container_name in [DATA_FEED_CONTAINER, REDIS_CONTAINER, REDIS_EXPORTER_CONTAINER]:
        for metric_type in [Metrics.MS_CPU, Metrics.MS_MEMORY]:
            metric = Metrics.ms_metrics[metric_type](pod_name, container_name)
            for agg in [AggregateFunction.ABSENT, AggregateFunction.AVG, AggregateFunction.MIN, AggregateFunction.MAX, AggregateFunction.P95]:
                for window in [RUN_ESTIMATION_FOR, 600]: # check different aggregation windows
                    window_key_name = 'run_duration' if window == RUN_ESTIMATION_FOR else (str(window) + 's')
                    metrics[AggregateFunction.query_functions[agg](metric, window)] = [metric_type, container_name, window_key_name, agg]

    return metrics
