import subprocess
import time

from perf.defines import PROM_PORT_FORWARD, PROM_POD_NAME, PROM_NAMESPACE


class PromConnection:
    def __init__(self):
        self.forward_prom_port_proc = None

    def start(self):
        print(f'[PromConnection] Forwarding Prometheus port {PROM_PORT_FORWARD}...')
        # TODO check success of Popen
        self.forward_prom_port_proc = subprocess.Popen(
            f'kubectl port-forward {PROM_POD_NAME} {PROM_PORT_FORWARD}:{PROM_PORT_FORWARD} -n {PROM_NAMESPACE}',
            shell=True,
            stdout=subprocess.DEVNULL,
        )
        # 5s to spin up
        wait = 5
        print(f'[PromConnection] Waiting {wait}s to spin up Prometheus connection...')
        time.sleep(wait)
        print(f'[PromConnection] Prometheus connection started on pid {self.forward_prom_port_proc.pid}')

    def stop(self):
        if self.forward_prom_port_proc is not None:
            self.forward_prom_port_proc.terminate()
            self.forward_prom_port_proc.wait()
            self.forward_prom_port_proc = None
            print(f'[PromConnection] Stopped forwarding Prometheus port')