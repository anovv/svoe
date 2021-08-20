# http://ec2-13-115-186-11.ap-northeast-1.compute.amazonaws.com:31380 istio-ingress public url
# https://github.com/kubeflow/kfctl/issues/140
import requests
import kfp

HOST = "http://ec2-13-115-186-11.ap-northeast-1.compute.amazonaws.com:31380/"
USERNAME = "admin@kubeflow.org"
PASSWORD = "12341234"
NAMESPACE = "kubeflow"

session = requests.Session()
response = session.get(HOST)

headers = {
    "Content-Type": "application/x-www-form-urlencoded",
}

data = {"login": USERNAME, "password": PASSWORD}
session.post(response.url, headers=headers, data=data)
session_cookie = session.cookies.get_dict()["authservice_session"]

# print(session_cookie)

client = kfp.Client(
    host=f"{HOST}/pipeline",
    cookies=f"authservice_session={session_cookie}",
    namespace=NAMESPACE,
)

pipelines = client.list_pipelines()

filtered = list(filter(lambda x: 'Demo' not in vars(x)['_name'] and 'Tutorial' not in vars(x)['_name'], vars(pipelines)['_pipelines']))

print(filtered)
