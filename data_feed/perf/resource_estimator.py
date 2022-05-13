# Script to run pods (without resource spec) and record resource consumptions (mem/cpu)
import time
import asyncio
import json
import yaml
import concurrent.futures
import subprocess
import atexit
from aiohttp import ClientSession

from kubernetes import client, config

# cluster should have prometheus, metrics-server, metrics-server-exporter and data-feed
# CLUSTER = 'k8s.vpc-apse1.dev.svoe.link'
CLUSTER = 'minikube-1'
DATA_FEED_NAMESPACE = 'data-feed'
DATA_FEED_CONTAINER = 'data-feed-container'
DATA_FEED_CM_CONFIG_NAME = 'data-feed-config.yaml'
REDIS_CONTAINER = 'redis'
# TODO dynamic parallelism based on heuristics
PARALLELISM = 2 # number of simultaneously running pods
RUN_FOR_S = 2*60 # how long to run a pod
PROM_NAMESPACE = 'monitoring'
PROM_POD_NAME = 'prometheus-kube-prometheus-stack-prometheus-0'
PROM_PORT_FORWARD = '9090'
PROM = f'http://localhost:{PROM_PORT_FORWARD}'
SAVE_TO = 'resources_estimation.json'

# TODO uncomment
config.load_kube_config(context=CLUSTER)
apps_api = client.AppsV1Api()
core_api = client.CoreV1Api()
data = {}
forward_prom_port_proc = None

def start_forward_prom_port():
    print(f'Forawrding Prometheus port {PROM_PORT_FORWARD}...')
    forward_port_proc = subprocess.Popen(
        f'kubectl port-forward {PROM_POD_NAME} {PROM_PORT_FORWARD}:{PROM_PORT_FORWARD} -n {PROM_NAMESPACE}', shell=True)
    # 5s to spin up
    wait = 5
    print(f'Waiting {5}s to spin up...')
    time.sleep(wait)
    print('Done')

@atexit.register
def stop_forward_prom_port():
    global forward_prom_port_proc
    if forward_prom_port_proc:
        forward_prom_port_proc.terminate()
        forward_prom_port_proc.wait()
        forward_prom_port_proc = None
        print(f'Stopped forwarding Prometheus port')

def load_ss_specs():
    specs = apps_api.list_namespaced_stateful_set(namespace=DATA_FEED_NAMESPACE)
    filtered = list(filter(lambda spec: should_estimate(spec), specs.items))
    print(f'Processing {len(filtered)}/{len(specs.items)} ss specs')
    return filtered

def set_env(ss_name, env):
    # https://stackoverflow.com/questions/71163299/how-to-update-env-variables-in-kubernetes-deployment-in-java
    apps_api.patch_namespaced_stateful_set(name=ss_name, namespace=DATA_FEED_NAMESPACE,
                                           body={'spec': {'template': {'spec': {'containers': [{'name': DATA_FEED_CONTAINER, 'env': [{'name': 'ENV', 'value': env}]}]}}}})
    print(f'Set ENV={env} for {ss_name}')

def scale_up(ss_name):
    apps_api.patch_namespaced_stateful_set_scale(name=ss_name, namespace=DATA_FEED_NAMESPACE,
                                                 body={'spec': {'replicas': 1}})
    print(f'Scaled up {ss_name}')

def wait_for_pod_to_run_for(pod_name, run_for_s):
    # TODO check status here and early exit if failure?
    print(f'Started waiting {RUN_FOR_S} for pod {pod_name} to run...')
    # for easier interrupts use for loop with short sleeps
    start = time.time()
    for i in range(int(run_for_s)):
        if i%5 == 0:
            print(f'Waiting for pod {pod_name}: {run_for_s - (time.time() - start)}s left')
        time.sleep(1)

    print(f'Done waiting for pod {pod_name} to finish')

def wait_for_pod_to(pod_name, appear, timeout):
    print(f'Waiting for pod {pod_name} to {"appear" if appear else "disappear"}...')
    start = time.time()
    while (time.time() - start < timeout):
        try:
            core_api.read_namespaced_pod(pod_name, DATA_FEED_NAMESPACE)
            if appear:
                print(f'Pod {pod_name} appeared')
                return True
        except:
            if not appear:
                print(f'Pod {pod_name} disappeared')
                return True
            pass
        time.sleep(1)

    print(f'Timeout waiting for pod {pod_name} to {"appear" if appear else "disappear"}')
    return False

def wait_for_pod_to_start_running(pod_name, timeout):
    # TODO long timeout only on image pull?
    # image pull may take up to 15 mins

    print(f'Waiting for pod {pod_name} to start running...')
    start = time.time()
    count = 0
    while (time.time() - start < timeout):
        pod = core_api.read_namespaced_pod(pod_name, DATA_FEED_NAMESPACE)
        pod_status_phase = pod.status.phase # Pending, Running, Succeeded, Failed, Unknown
        container_state, _ = get_container_state(pod.status) # running, terminated, waiting
        if (pod_status_phase == 'Running' and container_state == 'running'):
            print(f'Pod {pod_name}: {pod_status_phase}, Container: {container_state}')
            return True
        if (pod_status_phase == 'Failed'):
            print(f'Pod {pod_name}: {pod_status_phase}, Container: {container_state}')
            return False
        if count%5 == 0:
            print(f'Waiting for pod {pod_name}: {timeout - (time.time() - start)}s left until timeout, pod: {pod_status_phase}, container: {container_state}')
        count += 1
        time.sleep(1)

    print(f'Timeout waiting for pod {pod_name} to start running')
    return False

def scale_down(ss_name):
    apps_api.patch_namespaced_stateful_set_scale(name=ss_name, namespace=DATA_FEED_NAMESPACE,
                                                 body={'spec': {'replicas': 0}})
    print(f'Scaled down {ss_name}')


def estimate_resources(ss_name):
    pod_name = pod_name_from_ss(ss_name)
    cm_name = cm_name_from_ss(ss_name)
    payload, payload_hash = get_payload(cm_name)

    set_env(ss_name, 'TESTING')
    scale_up(ss_name)
    appeared = wait_for_pod_to(pod_name, True, 20)
    if appeared:
        runnning = wait_for_pod_to_start_running(pod_name, 15 * 60)
        if runnning:
            wait_for_pod_to_run_for(pod_name, RUN_FOR_S)

            loop = asyncio.get_event_loop()
            loop.run_until_complete(asyncio.gather(
                fetch_perf_metrics(pod_name, [DATA_FEED_CONTAINER, REDIS_CONTAINER]),
                fetch_health_metrics(pod_name, payload)
            ))

    finalize(ss_name)

def finalize(ss_name):
    scale_down(ss_name)
    set_env(ss_name, '')
    wait_for_pod_to(pod_name_from_ss(ss_name), False, 60)

def should_estimate(spec):
    for container in spec.spec.template.spec.containers:
        if container.name == DATA_FEED_CONTAINER \
                and container.resources.limits is None \
                and container.resources.requests is None:
            return True
    return False

async def _fetch_metric(metric, metric_name, metric_type, pod_name, session):
    params = {
        'query': metric,
    }
    async with session.get(PROM + '/api/v1/query', params=params) as response:
        resp = await response.json()
        res = resp['data']['result']
        if res:
            metric_value = resp['data']['result'][0]['value'][1]
        else:
            metric_value = '-1'

    print(metric_name + ' ' + metric_value)

    if pod_name not in data:
        data[pod_name] = {}
    if metric_type not in data[pod_name]:
        data[pod_name][metric_type] = {}

    data[pod_name][metric_type][metric_name] = metric_value

async def _fetch_metrics(metrics, metric_type, pod_name):
    tasks = []
    async with ClientSession() as session:
        for metric_name in metrics:
            tasks.append(asyncio.ensure_future(_fetch_metric(
                metrics[metric_name],
                metric_name,
                metric_type,
                pod_name,
                session
            )))

        await asyncio.gather(*tasks)


async def fetch_health_metrics(pod_name, payload):
    duration = f'[{RUN_FOR_S}s]'
    metrics = {}
    for exchange in payload_config:
        # TODO decide channel/data_type naming
        for data_type in payload_config[exchange]:
            for symbol in payload_config[exchange][data_type]:
                metrics.update({
                    # TODO add aggregation over other labels ?
                    # TODO if we have interrupts we need to check for absent() metric (otherwise avg will be counted only when pod was run, no info about interruptions)
                    # TODO separator instead of '_'
                    f'health_{data_type}_{symbol}': f'avg_over_time(svoe_data_feed_collector_conn_health_gauge{{exchange="{exchange}", symbol="{symbol}", data_type="{data_type}"}}{duration})'
                })

    await _fetch_metrics(metrics, 'health', pod_name)


async def fetch_perf_metrics(pod_name, containers):
    # https://github.com/olxbr/metrics-server-exporter to export metrics-server to prometheus
    duration = f'[{RUN_FOR_S}s]'
    metrics = {}
    for container_name in containers:
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

    await _fetch_metrics(metrics, 'perf', pod_name)

def save_data():
    with open(SAVE_TO, 'w+') as outfile:
        json.dump(data, outfile, indent=4, sort_keys=True)
    print(f'Saved data to {SAVE_TO}')

def get_payload(cm_name):
    cm = core_api.read_namespaced_config_map(cm_name, DATA_FEED_NAMESPACE)
    conf = yaml.load(cm.data[DATA_FEED_CM_CONFIG_NAME], Loader=yaml.SafeLoader)
    return conf['payload_config'], conf['payload_hash']

def pod_name_from_ss(ss_name):
    # ss manages pods have the same name as ss plus index, we assume 1 pod per ss
    # pod name example data-feed-binance-spot-6d1641b134-ss-0
    return ss_name + '-0'

def cm_name_from_ss(ss_name):
    return ss_name[:-2] + 'cm'

def get_container_state(pod_status):
    container_status = next(filter(lambda c: c.name == DATA_FEED_CONTAINER, pod_status.container_statuses), None)
    state = container_status.state
    if state.running:
        return 'running', state.running
    if state.terminated:
        return 'terminated', state.terminated
    if state.waiting:
        return 'waiting', state.waiting

def run_estimator():
    start_forward_prom_port()
    specs = load_ss_specs()
    with concurrent.futures.ThreadPoolExecutor(max_workers=PARALLELISM) as executor:
        futures = []
        for spec in specs:
            futures.append(executor.submit(estimate_resources, ss_name=spec.metadata.name))
        for future in concurrent.futures.as_completed(futures):
            print(future.result())
    save_data()
    stop_forward_prom_port()


# run_estimator()

# specs = apis_api.list_namespaced_stateful_set(namespace=DATA_FEED_NAMESPACE)
# for spec in specs.items:
#     print(spec.metadata.name)
# ss_name = specs.items[0].metadata.name
# apis_api.patch_namespaced_stateful_set_scale(name=ss_name, namespace=DATA_FEED_NAMESPACE, body={'spec': {'replicas': 0}})
# forward_prom_port()
# print(get_payload('data-feed-binance-spot-6d1641b134-cm'))
# load_ss_specs()
# loop = asyncio.get_event_loop()
# loop.run_until_complete(fetch_perf_metrics(PROM_POD_NAME, ['prometheus']))
# loop.run_until_complete(fetch_health_metrics('pod name'))
# save_data()
ss_name = 'data-feed-binance-spot-6d1641b134-ss'
pod_name = pod_name_from_ss(ss_name)
cm_name = cm_name_from_ss(ss_name)
payload, payload_hash = get_payload(cm_name)

set_env(ss_name, 'TESTING')
scale_up(ss_name)
appeared = wait_for_pod_to(pod_name, True, 20)
if not appeared:
    # TODO report timeout in data
    finalize(ss_name)
    exit()
runnning = wait_for_pod_to_start_running(pod_name, 15 * 60)
if not runnning:
    # TODO report timeout in data
    finalize(ss_name)
    exit()

wait_for_pod_to_run_for(pod_name, 10)
finalize(ss_name)
