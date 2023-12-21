from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

import attr

if TYPE_CHECKING:
    from ..models.ray_cluster_worker_group_config import RayClusterWorkerGroupConfig


T = TypeVar("T", bound="RayClusterConfig")


@attr.s(auto_attribs=True)
class RayClusterConfig:
    """
    Attributes:
        user_id (str):
        cluster_name (str):
        is_minikube (bool):
        enable_autoscaling (bool):
        head_cpu (float):
        head_memory (str):
        worker_groups (List['RayClusterWorkerGroupConfig']):
    """

    user_id: str
    cluster_name: str
    is_minikube: bool
    enable_autoscaling: bool
    head_cpu: float
    head_memory: str
    worker_groups: List["RayClusterWorkerGroupConfig"]
    additional_properties: Dict[str, Any] = attr.ib(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        user_id = self.user_id
        cluster_name = self.cluster_name
        is_minikube = self.is_minikube
        enable_autoscaling = self.enable_autoscaling
        head_cpu = self.head_cpu
        head_memory = self.head_memory
        worker_groups = []
        for worker_groups_item_data in self.worker_groups:
            worker_groups_item = worker_groups_item_data.to_dict()

            worker_groups.append(worker_groups_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "user_id": user_id,
                "cluster_name": cluster_name,
                "is_minikube": is_minikube,
                "enable_autoscaling": enable_autoscaling,
                "head_cpu": head_cpu,
                "head_memory": head_memory,
                "worker_groups": worker_groups,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.ray_cluster_worker_group_config import RayClusterWorkerGroupConfig

        d = src_dict.copy()
        user_id = d.pop("user_id")

        cluster_name = d.pop("cluster_name")

        is_minikube = d.pop("is_minikube")

        enable_autoscaling = d.pop("enable_autoscaling")

        head_cpu = d.pop("head_cpu")

        head_memory = d.pop("head_memory")

        worker_groups = []
        _worker_groups = d.pop("worker_groups")
        for worker_groups_item_data in _worker_groups:
            worker_groups_item = RayClusterWorkerGroupConfig.from_dict(worker_groups_item_data)

            worker_groups.append(worker_groups_item)

        ray_cluster_config = cls(
            user_id=user_id,
            cluster_name=cluster_name,
            is_minikube=is_minikube,
            enable_autoscaling=enable_autoscaling,
            head_cpu=head_cpu,
            head_memory=head_memory,
            worker_groups=worker_groups,
        )

        ray_cluster_config.additional_properties = d
        return ray_cluster_config

    @property
    def additional_keys(self) -> List[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
