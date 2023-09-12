import prefect
from prefect import task, Flow
from prefect.client.secrets import Secret
from prefect.tasks.aws.s3 import S3List

@task
def hello_task():
    # logger = prefect.context.get("logger")
    # logger.info("Hello world!")
    key = Secret("AWS_KEY").get()
    print(key)


with Flow("hello-flow") as flow:
    hello_task()

# flow.run()

list = S3List(bucket='svoe.test.1')
# res = list.run(prefix='parquet/BINANCE/l2_book/XLM-USDT')
res = list.run
print(res)