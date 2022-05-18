from defines import *
import enum
import subprocess
import time
import datetime
import json


class Result(str, enum.Enum):
    # TODO ss not found, ss already running, etc.
    STARTED_NOT_FINISHED = 'STARTED_NOT_FINISHED'
    POD_NOT_FOUND = 'POD_NOT_FOUND'
    POD_DIDNT_RUN = 'POD_DIDNT_RUN'
    METRICS_MISSING = 'METRICS_MISSING'
    ALL_OK = 'ALL_OK'
    INTERRUPTED = 'INTERRUPTED'


class PromConnection:
    def __init__(self):
        self.forward_prom_port_proc = None

    def start(self):
        print(f'Forawrding Prometheus port {PROM_PORT_FORWARD}...')
        # TODO check success of Popen
        self.forward_prom_port_proc = subprocess.Popen(
            f'kubectl port-forward {PROM_POD_NAME} {PROM_PORT_FORWARD}:{PROM_PORT_FORWARD} -n {PROM_NAMESPACE}',
            shell=True,
            stdout=subprocess.DEVNULL,
        )
        # 5s to spin up
        wait = 5
        print(f'Waiting {wait}s to spin up...')
        time.sleep(wait)
        print('Done')

    def stop(self):
        if self.forward_prom_port_proc is not None:
            self.forward_prom_port_proc.terminate()
            self.forward_prom_port_proc.wait()
            self.forward_prom_port_proc = None
            print(f'Stopped forwarding Prometheus port')


def save_data(data):
    if data is not None:
        path = f'resources-estimation-{datetime.datetime.now().strftime("%d-%m-%Y-%H:%M:%S")}.json'
        with open(path, 'w+') as outfile:
            json.dump(data, outfile, indent=4, sort_keys=True)
        print(f'Saved data to {path}')


def pod_name_from_ss(ss_name):
    # ss manages pods have the same name as ss plus index, we assume 1 pod per ss
    # pod name example data-feed-binance-spot-6d1641b134-ss-0
    return ss_name + '-0'


def cm_name_from_ss(ss_name):
    return ss_name[:-2] + 'cm'