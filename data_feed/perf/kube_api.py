from defines import *
from utils import cm_name_from_ss
import yaml
import kubernetes


class KubeApi:
    def __init__(self, core_api, apps_api):
        self.watcher = None
        self.core_api = core_api
        self.apps_api = apps_api

    def load_ss_names(self):
        specs = self.apps_api.list_namespaced_stateful_set(namespace=DATA_FEED_NAMESPACE)
        filtered_names = list(map(lambda spec: spec.metadata.name, filter(lambda spec: self.should_estimate(spec), specs.items)))
        print(f'Processing {len(filtered_names)}/{len(specs.items)} ss specs')
        return filtered_names

    def set_env(self, ss_name, env):
        # https://stackoverflow.com/questions/71163299/how-to-update-env-variables-in-kubernetes-deployment-in-java
        self.apps_api.patch_namespaced_stateful_set(name=ss_name, namespace=DATA_FEED_NAMESPACE,
                                               body={'spec': {'template': {'spec': {'containers': [{'name': DATA_FEED_CONTAINER, 'env': [{'name': 'ENV', 'value': env}]}]}}}})
        print(f'Set ENV={env} for {ss_name}')

    def scale_up(self, ss_name):
        self.apps_api.patch_namespaced_stateful_set_scale(name=ss_name, namespace=DATA_FEED_NAMESPACE,
                                                     body={'spec': {'replicas': 1}})
        print(f'Scaled up {ss_name}')

    def scale_down(self, ss_name):
        self.apps_api.patch_namespaced_stateful_set_scale(name=ss_name, namespace=DATA_FEED_NAMESPACE,
                                                     body={'spec': {'replicas': 0}})
        print(f'Scaled down {ss_name}')

    def get_payload(self, ss_name):
        cm_name = cm_name_from_ss(ss_name)
        cm = self.core_api.read_namespaced_config_map(cm_name, DATA_FEED_NAMESPACE)
        conf = yaml.load(cm.data[DATA_FEED_CM_CONFIG_NAME], Loader=yaml.SafeLoader)
        return conf['payload_config'], conf['payload_hash']

    @staticmethod
    def should_estimate(spec):
        for container in spec.spec.template.spec.containers:
            if container.name == DATA_FEED_CONTAINER \
                    and container.resources.limits is None \
                    and container.resources.requests is None:
                return True
        return False

    def check_health(self, pod_name):
        exec_command = [
            '/bin/sh',
            '-c',
            # TODO figure out correct script
            'echo \'import requests; print(requests.get("http://localhost:8000/metrics"))\' > p.py && python3 p.py && rm p.py']
        resp = kubernetes.stream.stream(self.core_api.connect_get_namespaced_pod_exec,
            pod_name,
            DATA_FEED_NAMESPACE,
            container=DATA_FEED_CONTAINER,
            command=exec_command,
            stderr=True, stdin=False,
            stdout=True, tty=False,
            _preload_content=True
        )
        print("Response: " + resp)