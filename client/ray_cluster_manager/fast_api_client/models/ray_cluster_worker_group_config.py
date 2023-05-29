from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

import attr

if TYPE_CHECKING:
    from ..models.ray_cluster_worker_group_config_ray_resources import RayClusterWorkerGroupConfigRayResources


T = TypeVar("T", bound="RayClusterWorkerGroupConfig")


@attr.s(auto_attribs=True)
class RayClusterWorkerGroupConfig:
    """
    Attributes:
        group_name (str):
        replicas (int):
        min_replicas (int):
        max_replicas (int):
        cpu (float):
        memory (str):
        ray_resources (RayClusterWorkerGroupConfigRayResources):
    """

    group_name: str
    replicas: int
    min_replicas: int
    max_replicas: int
    cpu: float
    memory: str
    ray_resources: "RayClusterWorkerGroupConfigRayResources"
    additional_properties: Dict[str, Any] = attr.ib(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        group_name = self.group_name
        replicas = self.replicas
        min_replicas = self.min_replicas
        max_replicas = self.max_replicas
        cpu = self.cpu
        memory = self.memory
        ray_resources = self.ray_resources.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "group_name": group_name,
                "replicas": replicas,
                "min_replicas": min_replicas,
                "max_replicas": max_replicas,
                "cpu": cpu,
                "memory": memory,
                "ray_resources": ray_resources,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.ray_cluster_worker_group_config_ray_resources import RayClusterWorkerGroupConfigRayResources

        d = src_dict.copy()
        group_name = d.pop("group_name")

        replicas = d.pop("replicas")

        min_replicas = d.pop("min_replicas")

        max_replicas = d.pop("max_replicas")

        cpu = d.pop("cpu")

        memory = d.pop("memory")

        ray_resources = RayClusterWorkerGroupConfigRayResources.from_dict(d.pop("ray_resources"))

        ray_cluster_worker_group_config = cls(
            group_name=group_name,
            replicas=replicas,
            min_replicas=min_replicas,
            max_replicas=max_replicas,
            cpu=cpu,
            memory=memory,
            ray_resources=ray_resources,
        )

        ray_cluster_worker_group_config.additional_properties = d
        return ray_cluster_worker_group_config

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
