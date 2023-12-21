from airflow import DAG
from airflow.operators.python import PythonOperator

from platform.client.fast_api_client.models import RayClusterWorkerGroupConfigRayResources, RayClusterConfig, RayClusterWorkerGroupConfig
from platform.client.ray_cluster_manager.ray_cluster_manager_client import RayClusterManagerClient


def test_ray_cluster_manager():
    client = RayClusterManagerClient()
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
            ray_resources=RayClusterWorkerGroupConfigRayResources.from_dict(
                {'worker_size_small': 9999999, 'instance_on_demand': 9999999})
        )]
    )
    print(client.delete_ray_cluster('test-ray-cluster'))
    print(client.create_ray_cluster(config))
    print(client.wait_until_ray_cluster_running('test-ray-cluster'))
    print(client.get_ray_cluster_status('test-ray-cluster'))
    print(client.list_ray_clusters())
    print(client.delete_ray_cluster('test-ray-cluster'))


dag = DAG(
    'test_ray_cluster_manager_dag',
    description='Test Ray Cluster Manager DAG',
    catchup=False
)

operator = PythonOperator(task_id='test_ray_cluster_manager_task', python_callable=test_ray_cluster_manager, dag=dag)

operator