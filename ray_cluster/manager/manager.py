import logging
import os
import time
from typing import Dict, List, Any, Tuple, Optional

import kubernetes
import yaml
from jinja2 import Template
from kubernetes.client import ApiException

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

from pydantic import BaseModel

GROUP = "ray.io"
VERSION = "v1alpha1"
PLURAL = "rayclusters"
KIND = "RayCluster"
RAYCLUSTER_TEMPLATE_PATH = f'{__location__}/yaml/raycluster-template.yaml'
RAY_NAMESPACE = 'ray-system' # TODO separate namespace for clusters?

log = logging.getLogger(__name__)


class RayClusterWorkerGroupConfig(BaseModel):
    group_name: str
    replicas: int
    min_replicas: int
    max_replicas: int
    cpu: float
    memory: str
    ray_resources: Dict


class RayClusterConfig(BaseModel):
    user_id: str
    cluster_name: str
    is_minikube: bool
    enable_autoscaling: bool
    head_cpu: float
    head_memory: str
    worker_groups: List[RayClusterWorkerGroupConfig]


class RayClusterManager:

    # kuberay/clients/python-client/python_client/kuberay_cluster_api.py has similar stuff but not packaged

    def __init__(self):
        if os.getenv('KUBERNETES_SERVICE_HOST'):
            # running inside kubernetes
            kubernetes.config.load_incluster_config()
        else:
            kubernetes.config.load_kube_config()

        self.custom_objects_api = kubernetes.client.CustomObjectsApi()

    def _ray_cluster_crd(self, config: RayClusterConfig):

        print(type(config.worker_groups[0]))
        # raise
        worker_groups_dicts = [dict(c) for c in config.worker_groups]
        # make ray_resources str representation from dict
        for w in worker_groups_dicts:
            ray_resources_dict = w['ray_resources']
            # '"{\"worker_size_small\": 9999999, \"instance_on_demand\": 9999999}"'
            ray_resources_str = '\'"{\\"'
            for k in ray_resources_dict:
                v = ray_resources_dict[k]
                ray_resources_str += str(k)
                ray_resources_str += '\\":'
                ray_resources_str += str(v)
                ray_resources_str += ', \\"'

            # remove last ', \"'
            ray_resources_str = ray_resources_str[:-4]
            ray_resources_str += '}"\''
            w['ray_resources'] = ray_resources_str
            # w['ray_resources'] = '\'"{\\"worker_size_small\\": 9999999, \\"instance_on_demand\\": 9999999}"\''

        return self._template_ray_cluster_crd(
            user_id=config.user_id,
            cluster_name=config.cluster_name,
            is_minikube=config.is_minikube, # TODO should this be part of config?
            enable_autoscaling=config.enable_autoscaling,
            head_cpu=config.head_cpu,
            head_memory=config.head_memory,
            worker_groups=worker_groups_dicts
        )

    def _template_ray_cluster_crd(
        self,
        user_id: str,
        cluster_name: str,
        is_minikube: bool,
        enable_autoscaling: bool,
        head_cpu: float,
        head_memory: str,
        worker_groups: List[Dict],
    ) -> Dict:
        crd = Template(open(RAYCLUSTER_TEMPLATE_PATH, 'r').read()).render(
            user_id=f'\'{user_id}\'',
            cluster_name=cluster_name,
            is_minikube=is_minikube,
            enable_autoscaling=enable_autoscaling,
            head_cpu=head_cpu,
            head_memory=head_memory,
            worker_groups=worker_groups
        )

        # uncomment to dump crd to yaml at path for debug
        # temp_file_path = f'gen/ray-cluster-{user_id}.yaml'
        # with open(temp_file_path, 'w+') as outfile:
        #     outfile.write(crd)
        return yaml.safe_load(crd)

    def list_ray_clusters(self, label_selector: str = '') -> Tuple[Any, Optional[str]]:
        try:
            resource: Any = self.custom_objects_api.list_namespaced_custom_object(
                group=GROUP,
                version=VERSION,
                plural=PLURAL,
                namespace=RAY_NAMESPACE,
                label_selector=label_selector,
            )
            if "items" in resource:
                return resource, None
            return None, '"items" field is not in response'
        except ApiException as e:
            if e.status == 404:
                err = "raycluster resource is not found. error = {}".format(e)
                log.error(err)
                return None, err
            else:
                err = "error fetching custom resource: {}".format(e)
                log.error(err)
                return None, err

    def get_ray_cluster(self, name: str) -> Tuple[Any, Optional[str]]:
        try:
            resource: Any = self.custom_objects_api.get_namespaced_custom_object(
                group=GROUP,
                version=VERSION,
                plural=PLURAL,
                name=name,
                namespace=RAY_NAMESPACE,
            )
            return resource, None
        except ApiException as e:
            if e.status == 404:
                err = "raycluster resource is not found. error = {}".format(e)
                log.error(err)
                return None, err
            else:
                err = "error fetching custom resource: {}".format(e)
                log.error(err)
                return None, err

    def get_ray_cluster_status(self, name: str, timeout: int = 60, delay_between_attempts: int = 1) -> Tuple[Any, Optional[str]]:
        while timeout > 0:
            try:
                resource: Any = self.custom_objects_api.get_namespaced_custom_object_status(
                    group=GROUP,
                    version=VERSION,
                    plural=PLURAL,
                    name=name,
                    namespace=RAY_NAMESPACE,
                )
            except ApiException as e:
                if e.status == 404:
                    err = "raycluster resource is not found. error = {}".format(e)
                    log.error(err)
                    return None, err
                else:
                    err = "error fetching custom resource: {}".format(e)
                    log.error(err)
                    return None, err

            if 'status' in resource and resource['status'] is not None:
                return resource['status'], None
            else:
                log.info("raycluster {} status not set yet, waiting...".format(name))
                time.sleep(delay_between_attempts)
                timeout -= delay_between_attempts

        err = "raycluster {} status not set yet, timing out...".format(name)
        log.info(err)

        # TODO this does not take into account pod statuses

        return None, err

    def wait_until_ray_cluster_running(self, name: str, timeout: int = 60, delay_between_attempts: int = 5) -> Tuple[bool, Optional[str]]:
        status, err = self.get_ray_cluster_status(name, timeout, delay_between_attempts)

        if status is None:
            return False, err

        if status['state'] != 'running':
            return False, status['reason']

        if 'head' not in status or 'serviceIP' not in status['head']:
            return False, 'Clusters head is not conneceted'

        # if status and status['head'] and status['head']['serviceIP'] and 'state' in status:
        #     if status['state'] == 'running':
        #         return True, None
        #     else:
        #         return False, status['reason']
        #
        return False, 'Cluster status is bad'

    def create_ray_cluster(self, config: RayClusterConfig) -> Tuple[bool, Optional[str]]:
        try:
            crd = self._ray_cluster_crd(config)
        except Exception as e:
            err = f'Unable to create crd from given RayClusterConfig: {e}'
            log.error(err)
            return False, err
        try:
            self.custom_objects_api.create_namespaced_custom_object(
                group=GROUP,
                version=VERSION,
                plural=PLURAL,
                body=crd,
                namespace=RAY_NAMESPACE,
            )
            return True, None
        except ApiException as e:
            if e.status == 409:
                err = "raycluster resource already exists. error = {}".format(e.reason)
                log.error(err)
                return False, err
            else:
                err = "error creating custom resource: {}".format(e)
                log.error(err)
                return False, err

    def delete_ray_cluster(self, name: str) -> Tuple[bool, Optional[str]]:
        try:
            self.custom_objects_api.delete_namespaced_custom_object(
                group=GROUP,
                version=VERSION,
                plural=PLURAL,
                name=name,
                namespace=RAY_NAMESPACE,
            )
            return True, None
        except ApiException as e:
            if e.status == 404:
                err = "raycluster custom resource is not found. error = {}".format(e.reason)
                log.error(err)
                return False, err
            else:
                err = "error deleting the raycluster custom resource: {}".format(e.reason)
                log.error(err)
                return False, err

    def patch_ray_cluster(self, name: str, ray_patch: Any) -> Tuple[bool, Optional[str]]:
        try:
            self.custom_objects_api.patch_namespaced_custom_object(
                group=GROUP,
                version=VERSION,
                plural=PLURAL,
                name=name,
                body=ray_patch,
                namespace=RAY_NAMESPACE,
            )
        except ApiException as e:
            err = "raycluster `{}` failed to patch, with error: {}".format(name, e)
            log.error(err)
            return False, err

        return True, None
