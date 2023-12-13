import unittest

from platform.ray_cluster.manager.manager import RayClusterManager, RayClusterWorkerGroupConfig, RayClusterConfig


class TestRayClusterManager(unittest.TestCase):


    # TODO example execing ray file
    # https://github.com/ray-project/kuberay/pull/1060/files

    def test(self):
        manager = RayClusterManager()
        config = RayClusterConfig(
            user_id='1',
            cluster_name='test-ray-cluster',
            is_minikube=True,
            enable_autoscaling=False,
            head_cpu=1,
            head_memory='3Gi',
            worker_groups=[RayClusterWorkerGroupConfig(
                group_name='workers',
                replicas=3,
                min_replicas=0,
                max_replicas=3,
                cpu=1,
                memory='3Gi',
                ray_resources={'worker_size_small': 9999999, 'instance_on_demand': 9999999}
            )]
        )
        res, err = manager.create_ray_cluster(config)
        # res = manager.delete_ray_cluster('test-ray-cluster')
        # res = manager.list_ray_clusters()
        print(res, err)

        # print(api.get_cluster_info('test-ray-cluster'))


if __name__ == '__main__':
    # unittest.main()
    t = TestRayClusterManager()
    t.test()
