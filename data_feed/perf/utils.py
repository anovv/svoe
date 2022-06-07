from defines import PROM_PORT_FORWARD, PROM_POD_NAME, PROM_NAMESPACE
import subprocess
import time
import json
import re


class PromConnection:
    def __init__(self):
        self.forward_prom_port_proc = None

    def start(self):
        print(f'Forwarding Prometheus port {PROM_PORT_FORWARD}...')
        # TODO check success of Popen
        self.forward_prom_port_proc = subprocess.Popen(
            f'kubectl port-forward {PROM_POD_NAME} {PROM_PORT_FORWARD}:{PROM_PORT_FORWARD} -n {PROM_NAMESPACE}',
            shell=True,
            stdout=subprocess.DEVNULL,
        )
        # 5s to spin up
        wait = 5
        print(f'Waiting {wait}s to spin up Prometheus connection...')
        time.sleep(wait)
        print('Prometheus connection started')

    def stop(self):
        if self.forward_prom_port_proc is not None:
            self.forward_prom_port_proc.terminate()
            self.forward_prom_port_proc.wait()
            self.forward_prom_port_proc = None
            print(f'Stopped forwarding Prometheus port')


class ResourceConvert:
    # https://github.com/amelbakry/kube-node-utilization/blob/master/nodeutilization.py
    def cpu(value):
        """
        Return CPU in milicores if it is configured with value
        """
        if re.match(r"[0-9]{1,9}m", str(value)):
            cpu = re.sub("[^0-9]", "", value)
        elif re.match(r"[0-9]{1,4}$", str(value)):
            cpu = int(value) * 1000
        elif re.match(r"[0-9]{1,15}n", str(value)):
            cpu = int(re.sub("[^0-9]", "", value)) // 1000000
        elif re.match(r"[0-9]{1,15}u", str(value)):
            cpu = int(re.sub("[^0-9]", "", value)) // 1000
        return int(cpu)

    def memory(value):
        """
        Return Memory in MB
        """
        if re.match(r"[0-9]{1,9}Mi?", str(value)):
            mem = re.sub("[^0-9]", "", value)
        elif re.match(r"[0-9]{1,9}Ki?", str(value)):
            mem = re.sub("[^0-9]", "", value)
            mem = int(mem) // 1024
        elif re.match(r"[0-9]{1,9}Gi?", str(value)):
            mem = re.sub("[^0-9]", "", value)
            mem = int(mem) * 1024
        return int(mem)


def save_data(data):
    if data is not None:
        # TODO
        # path = f'resources-estimation-{datetime.datetime.now().strftime("%d-%m-%Y-%H:%M:%S")}.json'
        path = 'resources-estimation.json'
        with open(path, 'w+') as outfile:
            json.dump(data, outfile, indent=4, sort_keys=True)
        print(f'Saved data to {path}')


def pod_name_from_ss(ss_name):
    # ss manages pods have the same name as ss plus index, we assume 1 pod per ss
    # pod name example data-feed-binance-spot-6d1641b134-ss-0
    return ss_name + '-0'


def raw_pod_name_from_ss(ss_name):
    # raw pod strips '-ss' suffix, adds '-raw'
    return ss_name[:-3] + '-raw'


def cm_name_from_ss(ss_name):
    return ss_name[:-2] + 'cm'


def equal_dicts(d1, d2, compare_by_keys):
    if not d1 or not d2:
        return d1 == d2
    return filtered_dict(d1, compare_by_keys) == \
           filtered_dict(d2, compare_by_keys)


def filtered_dict(d, filter_keys):
    if not d:
        return d
    return {k: v for k, v in d.items() if k in filter_keys}
