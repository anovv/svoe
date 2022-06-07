import kubernetes
import time
import subprocess
import pathlib

from ..kube_api import KubeApi
from ..kube_watcher.kube_watcher import KubeWatcher
from ..defines import *


class Scheduler:
    def __init__(self):
        kubernetes.config.load_kube_config(context=CLUSTER)
        core_api = kubernetes.client.CoreV1Api()
        apps_api = kubernetes.client.AppsV1Api()
        custom_objects_api = kubernetes.client.CustomObjectsApi()
        scheduling_api = kubernetes.client.SchedulingV1Api()
        self.kube_api = KubeApi(core_api, apps_api, custom_objects_api, scheduling_api)
        self.kube_watcher = KubeWatcher(core_api, [self.callback])

    def callback(self, event):
        print(event)

    def set_oom_score_adj(self, node, pod, containers, score):
        container_names = ""
        for container in containers:
            container_names += (container + "_" + pod + " ")
        container_names = container_names[:-1]
        path = pathlib.Path(__file__).parent.resolve()
        process = subprocess.Popen(
            [f'{path}/set_containers_oom_score_adj.sh', f'-c "{container_names}"', f'-n {node}', f'-s "{score}"'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, _ = process.communicate()
        print(stdout.decode("utf-8"))

    def get_oom_score(self, node, pod, containers):
        container_names = ""
        for container in containers:
            container_names += (container + "_" + pod + " ")
        container_names = container_names[:-1]
        path = pathlib.Path(__file__).parent.resolve()
        process = subprocess.Popen(
            [f'{path}/get_containers_oom_score.sh', f'-c "{container_names}"', f'-n {node}'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, _ = process.communicate()
        print(stdout.decode("utf-8"))

    def get_node(self):
        return


    def run(self, ss_names):
        # self.kube_watcher.start()
        for ss_name in ss_names:
            print(f'Scheduling {ss_name}...')
            # TODO set restartPolicy=Never
            # TODO set pod priorities
            self.kube_api.set_env(ss_name, 'TESTING')
            self.kube_api.scale_up(ss_name)
            time.sleep(30)
        time.sleep(3600)

    def stop(self):
        return  # TODO
