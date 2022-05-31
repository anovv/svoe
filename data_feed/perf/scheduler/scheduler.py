import kubernetes
from ..kube_api import KubeApi
from ..kube_watcher.kube_watcher import KubeWatcher
import time


class Scheduler:
    def __int__(self):
        core_api = kubernetes.client.CoreV1Api()
        apps_api = kubernetes.client.AppsV1Api()
        self.kube_api = KubeApi(core_api, apps_api)
        self.kube_watcher = KubeWatcher(core_api, [self.callback])

    def callback(self, event):
        print(event)

    def run(self, ss_names):
        self.kube_watcher.start()
        # for ss_name in ss_names:
        #     print(f'Scheduling {ss_name}...')
        #     TODO set restartPolicy=Never
        #     TODO set pod priorities
        #     self.kube_api.set_env(ss_name, 'TESTING')
        #     self.kube_api.scale_up(ss_name)
        #     time.sleep(30)
        time.sleep(3600)

    def stop(self):
        return # TODO