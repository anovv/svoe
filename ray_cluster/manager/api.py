from typing import Dict, Tuple, List

import kubernetes
import yaml
from jinja2 import Template

RAYCLUSTER_CONF_PATH = 'yaml/raycluster-template.yaml'
RAY_NAMESPACE = 'ray-system' # TODO separate namespace for clusters?

class RayClusterManagerApi:

    # TODO kuberay/clients/python-client/python_client/kuberay_cluster_api.py has similar stuff but not packaged
    # https://github.com/ray-project/kuberay/blob/master/clients/python-client/python_client_test/test_api.py

    def __init__(self, kube_ctx: str):
        kubernetes.config.load_kube_config(context=kube_ctx)
        self.custom_objects_api = kubernetes.client.CustomObjectsApi()

    def template_ray_cluster_crd(
        self,
        user_id: str,
        cluster_name: str,
        is_minikube: bool,
        enable_autoscaling: bool,
        head_cpu: float,
        head_memory: str,
        worker_groups: List[Dict],
    ):
        crd = Template(open(RAYCLUSTER_CONF_PATH, 'r').read()).render(
            user_id=f'\'{user_id}\'',
            cluster_name=cluster_name,
            is_minikube=is_minikube,
            enable_autoscaling=enable_autoscaling,
            head_cpu=head_cpu,
            head_memory=head_memory,
            worker_groups=worker_groups
        )

        # uncomment to dump crd to yaml at path for debug
        temp_file_path = f'gen/ray-cluster-{user_id}.yaml'
        with open(temp_file_path, 'w+') as outfile:
            outfile.write(crd)
        return yaml.safe_load(crd)

    def request_cluster(self, conf: Dict):
        return self.custom_objects_api.create_namespaced_custom_object(
            group='ray.io',
            version='v1alpha1',
            plural='rayclusters',
            namespace=RAY_NAMESPACE,
            body=conf
        )

    def get_cluster_info(self, cluster_name: str):
        # return self.custom_objects_api.get_namespaced_custom_object(
        return self.custom_objects_api.get_namespaced_custom_object_status(
            group='ray.io',
            version='v1alpha1',
            plural='rayclusters',
            namespace=RAY_NAMESPACE,
            name=cluster_name
        )