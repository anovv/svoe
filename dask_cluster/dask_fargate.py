from dask_cloudprovider.aws import FargateCluster


class HackyDict(dict):
    # hack lmao
    # blacklists a 'launchType' key to pass down to Dask Worker/Scheduler config
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

    def __setattr__(self, key, value):
        if key in ['launchType']:
            return  # silent fail
        else:
            super().__setattr__(key, value)

    def __setitem__(self, key, value):
        if key in ['launchType']:
            return  # silent fail
        else:
            super().__setitem__(key, value)

    def copy(self):
        return type(self)(self)

    # def __copy__(self):
    #     cls = self.__class__
    #     result = cls.__new__(cls)
    #     result.__dict__.update(self.__dict__)
    #     return result


class SvoeTestDaskCluster(FargateCluster):
    def __init__(self, **kwargs):
        capacity_provider_fargate_config = HackyDict({
            'capacityProviderStrategy': [{
                'capacityProvider': 'FARGATE'
            }]
        })

        capacity_provider_fargate_spot_config = HackyDict({
            'capacityProviderStrategy': [{
                'capacityProvider': 'FARGATE_SPOT'
            }]
        })

        super().__init__(
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
            find_address_timeout=90, # TODO fix https://github.com/dask/dask-cloudprovider/issues/313 to speed up boot time
            worker_task_kwargs=HackyDict(capacity_provider_fargate_spot_config),
            scheduler_task_kwargs=HackyDict(capacity_provider_fargate_config),
            environment=
            {
                'EXTRA_PIP_PACKAGES': 'pyarrow s3fs prefect[aws] fastparquet numpy', # TODO use prebuild docker image to speed up boot time
            },
            **kwargs
        )

# cluster = SvoeTestDaskCluster()
# cluster.status
# cluster.adapt(minimum=1, maximum=20)
# client = Client(cluster)
