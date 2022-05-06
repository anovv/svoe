# Script to run pods (without resource spec) and record resource consumptions (mem/cpu)
import time
import asyncio
import aiofiles
import json
import concurrent.futures
from aiohttp import ClientSession

from kubernetes import client, config

CLUSTER = 'k8s.vpc-apse1.dev.svoe.link'
DATA_FEED_NAMESPACE = 'data_feed'
PARALLELISM = 1 # number of simultaneously running pods
RUN_FOR_S = 5*60 # how long to run a pod
PROM_NAMESPACE = 'monitoring'
PROM_POD_NAME = 'TODO'
PROM_PORT_FORWARD = 1228
PROM = f'http://localhost:{PROM_PORT_FORWARD}'
SAVE_TO = 'resources_estimation.json'

config.load_kube_config(context=CLUSTER)
apis_api = client.AppsV1Api()
# core_api = client.CoreV1Api()

def get_ss_specs():
    return apis_api.list_namespaced_stateful_set(namespace=DATA_FEED_NAMESPACE)

def scale_up_and_wait(ss_id, specs):
    name = '' # TODO get by ss_id
    apis_api.patch_namespaced_stateful_set_scale(name=name, namespace=DATA_FEED_NAMESPACE, body={'spec': {'replicas': 1}})
    time.sleep(RUN_FOR_S)

def scale_down(ss_id, specs):
    name = '' # TODO get by ss_id
    apis_api.patch_namespaced_stateful_set_scale(name=name, namespace=DATA_FEED_NAMESPACE, body={'spec': {'replicas': 0}})

def estimate_resources(ss_id, specs):
    # TODO check if ss needs estimation first
    scale_up_and_wait(ss_i, specs)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(record_prom_metrics(ss_id))
    scale_down(ss_id, specs)

async def fetch_and_save_prom_metric(metric, metric_name, pod_name, session):
    params = {
        'query': metric,
    }
    async with session.get(PROM + '/api/v1/query', params=params) as response:
        res = await response.json()['data']['result']

    async with aiofiles.open(SAVE_TO, mode='r+') as f:
        contents = await f.read()
        data = json.loads(contents)
        data[pod_name][metric_name] = res # TODO units for cpu/mem
        await f.write(json.dumps(data))

async def record_prom_metrics(ss_id, specs):
    # https://github.com/olxbr/metrics-server-exporter to export metrics-server to prometheus
    pod_name = '' # TODO get by ss_id
    duration = f'[{RUN_FOR_S}s]'
    metrics = {}
    for container_name in ['data_feed', 'redis']:
        metrics.update({
            # mem
            f'mem_avg_{container_name}': f'avg_over_time(kube_metrics_server_pods_mem{{pod_name="{pod_name}", pod_container_name="{container_name}"}}{duration})',
            f'mem_max_{container_name}': f'max_over_time(kube_metrics_server_pods_mem{{pod_name="{pod_name}", pod_container_name="{container_name}"}}{duration})',
            f'mem_min_{container_name}': f'min_over_time(kube_metrics_server_pods_mem{{pod_name="{pod_name}", pod_container_name="{container_name}"}}{duration})',
            f'mem_095_{container_name}': f'quantile_over_time(0.95, kube_metrics_server_pods_mem{{pod_name="{pod_name}", pod_container_name="{container_name}"}}{duration})',
            # cpu
            f'cpu_avg_{container_name}': f'avg_over_time(kube_metrics_server_pods_cpu{{pod_name="{pod_name}", pod_container_name="{container_name}"}}{duration})',
            f'cpu_max_{container_name}': f'max_over_time(kube_metrics_server_pods_cpu{{pod_name="{pod_name}", pod_container_name="{container_name}"}}{duration})',
            f'cpu_min_{container_name}': f'min_over_time(kube_metrics_server_pods_cpu{{pod_name="{pod_name}", pod_container_name="{container_name}"}}{duration})',
            f'cpu_095_{container_name}': f'quantile_over_time(0.95, kube_metrics_server_pods_cpu{{pod_name="{pod_name}", pod_container_name="{container_name}"}}{duration})',
        })

    tasks = []
    async with ClientSession() as session:
        for metric_name, metric in metrics:
            tasks.append(asyncio.ensure_future(fetch_and_save_prom_metric(metric, metric_name, pod_name, session)))
        await asyncio.gather(*tasks)

def forward_prom_port():
    api_instance.connect_get_namespaced_pod_portforward(name=PROM_POD_NAME, namespace=PROM_NAMESPACE, ports=PROM_PORT_FORWARD)

def run_estimator():
    specs = get_ss_specs()
    with concurrent.futures.ThreadPoolExecutor(max_workers=PARALLELISM) as executor:
        futures = []
        for ss_id in specs:
            futures.append(executor.submit(estimate_resources, ss_id=ss_id, specs=specs))
        for future in concurrent.futures.as_completed(futures):
            print(future.result())

run_estimator()
