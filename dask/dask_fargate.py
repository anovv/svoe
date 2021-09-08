from dask_cloudprovider.aws import FargateCluster
import dask.dataframe as dd
from dask import delayed
import dask
from dask.distributed import Client

# needs existing vpc, subnets and security groups (or will default to creating new ones)
# vpc-0b7a5ea241a581217 - tokyokopscluster.k8s.local
# subnet-0af71c701fb97aca3 - "ap-northeast-1a.tokyokopscluster.k8s.local
# sg-0822216274a1e23a1 - nodes.tokyokopscluster.k8s.local Security group for nodes

# To use existing arn arn:aws:ecs:ap-northeast-1:050011372339:cluster/dask-5a84c0be-0

cluster = FargateCluster(
    vpc="vpc-0b7a5ea241a581217",
    subnets=["subnet-0af71c701fb97aca3"],
    security_groups=["sg-0822216274a1e23a1"],
    n_workers=1,
    worker_cpu=512,
    worker_mem=1024,
    scheduler_cpu=512,
    scheduler_mem=1024,
    scheduler_timeout="30 minutes",
    environment={'EXTRA_PIP_PACKAGES': 'pyarrow s3fs'}
)

cluster.adapt(minimum=1, maximum=20)
client = Client(cluster)

# cluster = FargateCluster(cluster_arn="arn:aws:ecs:ap-northeast-1:050011372339:cluster", vpc="vpc-0b7a5ea241a581217")

bucket = 's3://svoe.test.1/parquet/FTX/l2_book/BTC-USD'

def ping(addr):
    import requests
    return requests.get(addr).status_code

results = []
for i in range(1000):
    results.append(delayed(ping)('https://www.google.com'))

total = delayed(sum)(results)
total.compute()

def boto_bucket_exists():
    import boto3
    s3 = boto3.resource('s3')
    return str(s3.meta.client.head_bucket(Bucket='svoe.test.1'))

def install_package():
    import os
    os.system("pip install pyarrow")

client.run(install_package)

storage_options={'key': 'AKIAJXSXXFCA3HN3T7GQ', 'secret': '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'}
d = dask.delayed(dd.read_parquet)('s3://svoe.test.1/parquet/FTX/l2_book/BTC-USD', storage_options=storage_options)
df = dask.compute(d)[0]