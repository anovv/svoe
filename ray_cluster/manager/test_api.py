import unittest

from ray_cluster.manager.api import RayClusterManagerApi


class TestRayClusterManagerApi(unittest.TestCase):

    def test(self):
        api = RayClusterManagerApi('minikube-1')
        conf = api.template_ray_cluster_crd(
            user_id='1',
            cluster_name='test-ray-cluster',
            is_minikube=True,
            enable_autoscaling=False,
            head_cpu=1,
            head_memory='3Gi',
            worker_groups=[{
                'group_name': 'workers',
                'replicas': 3,
                'min_replicas': 0,
                'max_replicas': 3,
                'cpu': 1,
                'memory': '3Gi',
                'ray_resources': '\'"{\\"worker_size_small\\": 9999999, \\"instance_on_demand\\": 9999999}"\'',
            }]
        )
        res = api.request_cluster(conf)
        print(res)

        # print(api.get_cluster_info('test-ray-cluster'))


if __name__ == '__main__':
    # unittest.main()
    t = TestRayClusterManagerApi()
    t.test()