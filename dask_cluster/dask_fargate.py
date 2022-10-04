from dask_cloudprovider.aws import FargateCluster

# to get all tasks
# https://github.com/dask/distributed/issues/3263
class SvoeDaskCluster(FargateCluster):
    def __init__(self, **kwargs):
        super().__init__(
            fargate_spot=True,
            cluster_arn="arn:aws:ecs:ap-northeast-1:050011372339:cluster/dask-svoe-test-1",
            vpc="vpc-0b7a5ea241a581217",
            subnets=["subnet-0af71c701fb97aca3"],
            security_groups=["sg-0822216274a1e23a1"],
            n_workers=2,
            worker_cpu=512,
            worker_mem=1024,
            scheduler_cpu=512,
            scheduler_mem=1024,
            scheduler_timeout="30 minutes",
            find_address_timeout=120,
            environment=
            {
                'EXTRA_PIP_PACKAGES': 'pyarrow s3fs prefect[aws] fastparquet numpy order-book intervaltree prefect-dask awswrangler boto3 prefect-aws streamz frozenlist',
                # TODO use prebuild docker image to speed up boot time
                # TODO set AWS credentials env vars
            },
            **kwargs
        )

# cluster = SvoeTestDaskCluster()
# cluster.status
# cluster.adapt(minimum=1, maximum=20)
# client = Client(cluster)
