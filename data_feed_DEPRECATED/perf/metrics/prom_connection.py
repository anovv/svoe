import subprocess
import time

from perf.defines import PROM_PORT_FORWARD, PROM_POD_NAME, PROM_NAMESPACE


class PromConnection:
    def __init__(self):
        self.forward_prom_port_proc = None
        self.running = False

    def start(self):
        self.running = True
        print(f'[PromConnection] Forwarding Prometheus port {PROM_PORT_FORWARD}...')
        # TODO check success of Popen
        # TODO https://stackoverflow.com/questions/47484312/kubectl-port-forwarding-timeout-issue
        # TODO fix error creating error stream for port 9090 -> 9090: Timeout occurred
        self.forward_prom_port_proc = subprocess.Popen(
            f'kubectl port-forward {PROM_POD_NAME} {PROM_PORT_FORWARD}:{PROM_PORT_FORWARD} -n {PROM_NAMESPACE}',
            shell=True,
            stdout=subprocess.DEVNULL,
        )
        if not self.running:
            return
        # 5s to spin up
        wait = 5
        print(f'[PromConnection] Waiting {wait}s to spin up Prometheus connection...')
        time.sleep(wait)
        if not self.running:
            return
        print(f'[PromConnection] Prometheus connection started on pid {self.forward_prom_port_proc.pid}')

    def stop(self):
        if not self.running:
            return
        self.running = False
        if self.forward_prom_port_proc is not None:
            self.forward_prom_port_proc.terminate()
            self.forward_prom_port_proc.wait()
            self.forward_prom_port_proc = None
            print(f'[PromConnection] Stopped forwarding Prometheus port')