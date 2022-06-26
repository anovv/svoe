import math
import yaml
import json
import kubernetes

from perf.utils import parse_timestamp_string
from perf.defines import CLUSTER, \
    DATA_FEED_CONTAINER, DATA_FEED_CM_CONFIG_NAME, DATA_FEED_NAMESPACE, \
    REMOTE_SCRIPTS_DS_CONTAINER, REMOTE_SCRIPTS_DS_NAMESPACE, REMOTE_SCRIPTS_DS_LABEL_SELECTOR
from perf.kube_api.utils import cm_name_pod_name, ss_name_from_pod_name, pod_name_from_ss_name
from perf.kube_api.resource_convert import ResourceConvert


class KubeApi:
    @staticmethod
    def new_instance():
        kubernetes.config.load_kube_config(context=CLUSTER)
        core_api = kubernetes.client.CoreV1Api()
        apps_api = kubernetes.client.AppsV1Api()
        custom_objects_api = kubernetes.client.CustomObjectsApi()
        scheduling_api = kubernetes.client.SchedulingV1Api()
        return KubeApi(core_api, apps_api, custom_objects_api, scheduling_api)

    def __init__(self, core_api, apps_api, custom_objects_api, scheduling_api):
        self.core_api = core_api
        self.apps_api = apps_api
        self.custom_objects_api = custom_objects_api
        self.scheduling_api = scheduling_api
        self.priority_pool = {}
        self.remote_scripts_ds_pod_cache = {}

    def get_nodes(self):
        return self.core_api.list_node()

    def get_nodes_resource_usage(self):
        # needs metrics-server running
        # https://stackoverflow.com/questions/66453590/how-to-use-kubectl-top-node-in-kubernetes-python
        try:
            k8s_nodes = self.custom_objects_api.list_cluster_custom_object("metrics.k8s.io", "v1beta1", "nodes")
            res = {}
            for item in k8s_nodes['items']:
                node_name = item['metadata']['name']
                res[node_name] = {
                    'cpu': ResourceConvert.cpu(item['usage']['cpu']),
                    'memory': ResourceConvert.memory(item['usage']['memory']),
                    'cluster_timestamp': parse_timestamp_string(item['timestamp']),
                }
            return True, res
        except kubernetes.client.exceptions.ApiException as e:
            if e.reason == 'Service Unavailable':
                return False, e.reason
            else:
                raise e
        except Exception as e:
            raise e

    def load_pod_names_from_ss(self, subset=None):
        specs = self.apps_api.list_namespaced_stateful_set(namespace=DATA_FEED_NAMESPACE)
        filtered_ss_names = list(map(lambda spec: spec.metadata.name, filter(lambda spec: self.should_estimate(spec), specs.items)))
        if subset is not None and len(subset) > 0:
            filtered_ss_names = list(filter(lambda name: name in subset, filtered_ss_names))
        pod_names = list(map(lambda name: pod_name_from_ss_name(name), filtered_ss_names))
        print(f'Processing {len(filtered_ss_names)}/{len(specs.items)} ss specs')
        return pod_names

    def pod_template_from_ss(self, pod_name):
        ss_name = ss_name_from_pod_name(pod_name)
        resp = self.apps_api.list_namespaced_stateful_set(
            namespace=DATA_FEED_NAMESPACE,
            field_selector=f'metadata.name={ss_name}',
            _preload_content=False,
        )
        # TODO edge check
        return json.loads(resp.data)['items'][0]['spec']['template']

    def get_or_create_priority_class(self, priority):
        if priority in self.priority_pool:
            return self.priority_pool[priority]
        name = f'data-feed-estimation-priority-class-{priority}' if priority >= 0 else f'data-feed-estimation-priority-class-negative-{int(math.fabs(priority))}'
        definition = {
            'apiVersion': 'scheduling.k8s.io/v1',
            'kind': 'PriorityClass',
            'metadata': {
                'name': name
            },
            'value': priority,
            'globalDefault': False,
            'description': f'PriorityClass for data-feed pods for estimation runs. Value: {priority}'
        }
        try:
            self.scheduling_api.create_priority_class(body=definition)
        except kubernetes.client.exceptions.ApiException as e:
            if json.loads(e.body)['reason'] == 'AlreadyExists':
                self.priority_pool[priority] = name
            else:
                raise e
        self.priority_pool[priority] = name
        return name

    def create_raw_pod(self, pod_name, node_name, pod_priority):
        definition = {
            'apiVersion': 'v1',
            'kind': 'Pod'
        }

        template = self.pod_template_from_ss(pod_name)
        template['metadata']['name'] = pod_name
        template['spec']['restartPolicy'] = 'Never'
        template['spec']['priorityClassName'] = self.get_or_create_priority_class(pod_priority)

        template['spec']['affinity']['nodeAffinity']['requiredDuringSchedulingIgnoredDuringExecution']['nodeSelectorTerms'][0]['matchExpressions'].append({
            'key': 'kubernetes.io/hostname',
            'operator': 'In',
            'values': [node_name]
        })

        # set env for DATA_FEED_CONTAINER
        for container in template['spec']['containers']:
            if container['name'] == DATA_FEED_CONTAINER:
                env_vars = container['env']
                has_env_var = False
                for env_var in env_vars:
                    if env_var['name'] == 'ENV':
                        env_var['value'] = 'TESTING'
                        has_env_var = True
                        break
                if not has_env_var:
                    env_vars.append({'name': 'ENV', 'value': 'TESTING'})

        template['spec']['tolerations'].append({
            'key': 'svoe-role',
            'value': 'resource-estimator',
            'operator': 'Equal',
            'effect': 'NoSchedule'
        })

        definition.update(template)
        # TODO success check
        self.core_api.create_namespaced_pod(body=definition, namespace=DATA_FEED_NAMESPACE)

    def delete_raw_pod(self, pod_name):
        self.core_api.delete_namespaced_pod(name=pod_name, namespace=DATA_FEED_NAMESPACE)

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

    def get_payload(self, pod_name):
        cm_name = cm_name_pod_name(pod_name)
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

    def pod_exec(self, namespace, pod_name, container_name, cmd):
        return kubernetes.stream.stream(self.core_api.connect_get_namespaced_pod_exec,
            pod_name,
            namespace,
            container=container_name,
            command=cmd,
            stderr=True, stdin=False,
            stdout=True, tty=False,
            _preload_content=True
        )

    def execute_remote_script(self, script_string, node_name):
        cmd = ['nsenter', '--mount=/proc/1/ns/mnt', '--', 'bash', '-c', script_string]
        if node_name not in self.remote_scripts_ds_pod_cache:
            print(f'[KubeApi] Stale cache for remote-scripts-ds pod, updating...')
            self.remote_scripts_ds_pod_cache[node_name] = self.get_remote_scripts_pod(node_name)
        remote_scripts_pod = self.remote_scripts_ds_pod_cache[node_name]
        if remote_scripts_pod is None:
            return
        try:
            return self.pod_exec(
                REMOTE_SCRIPTS_DS_NAMESPACE,
                remote_scripts_pod,
                REMOTE_SCRIPTS_DS_CONTAINER,
                cmd
            )
        except kubernetes.client.exceptions.ApiException as e:
            if e.reason == 'Handshake status 404 Not Found':
                # cache stale, ask kube for latest remote-scripts-ds pod
                print(f'[KubeApi] Stale cache for remote-scripts-ds pod, updating...')
                remote_scripts_pod = self.get_remote_scripts_pod(node_name)
                if remote_scripts_pod is None:
                    return
                self.remote_scripts_ds_pod_cache[node_name] = remote_scripts_pod
                return self.pod_exec(
                    REMOTE_SCRIPTS_DS_NAMESPACE,
                    remote_scripts_pod,
                    REMOTE_SCRIPTS_DS_CONTAINER,
                    cmd
                )
            else:
                # TODO handle kubernetes.client.exceptions.ApiException: (0)
                # Reason: Handshake status 500 Internal Server Error
                # when remote-scripts pod is not available
                raise e

    def get_remote_scripts_pod(self, node_name):
        res = self.core_api.list_namespaced_pod(
            namespace=REMOTE_SCRIPTS_DS_NAMESPACE,
            field_selector=f'spec.nodeName={node_name}',
            label_selector=REMOTE_SCRIPTS_DS_LABEL_SELECTOR,
        )
        try:
            return res.items[0].metadata.name
        except Exception as e:
            print(f'[KubeApi] Unable to get remote-scripts-ds pod for node {node_name}')
            return None
