import requests

URL = 'http://127.0.0.1:1414'

def list_clusters(namespace):
    url = f'{URL}/apis/v1alpha2/namespaces/{namespace}/clusters'
    r = requests.get(url)
    return r


print(list_clusters('ray_system'))