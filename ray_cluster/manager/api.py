from typing import Dict, Tuple, List

from jinja2 import Template

RAYCLUSTER_CONF_PATH = 'yaml/raycluster-template.yaml'
GEN_PATH = 'gen'

class RayClusterManagerApi:

    def __init__(self, kube_ctx: str):
        self.kube_ctx = kube_ctx

    def template_ray_cluster_crd(
        self,
        user_id: str,
        cluster_name: str,
        is_minikube: bool,
        enable_autoscaling: bool,
        head_cpu: float,
        head_memory: str,
        worker_groups: List[Dict],
    ) -> str:
        crd = Template(open(RAYCLUSTER_CONF_PATH, 'r').read()).render(
            user_id=user_id,
            cluster_name=cluster_name,
            is_minikube=is_minikube,
            enable_autoscaling=enable_autoscaling,
            head_cpu=head_cpu,
            head_memory=head_memory,
            worker_groups=worker_groups
        )
        temp_file_path = f'{GEN_PATH}/ray-cluster-{user_id}.yaml'
        # TODO concurrency/lock?
        with open(temp_file_path, 'w+') as outfile:
            outfile.write(crd)
        return temp_file_path

    def launch_cluster(self):
        # TODO call kube api
        return