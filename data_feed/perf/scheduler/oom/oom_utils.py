import subprocess
import pathlib

def set_oom_score_adj(self, node, pod, containers, score):
    container_names = ""
    for container in containers:
        container_names += (container + "_" + pod + " ")
    container_names = container_names[:-1]
    path = pathlib.Path(__file__).parent.resolve()
    process = subprocess.Popen(
        [f'{path}/set_containers_oom_score_adj.sh', f'-c "{container_names}"', f'-n {node}', f'-s "{score}"'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, _ = process.communicate()
    print(stdout.decode("utf-8"))


def get_oom_score(self, node, pod, containers):
    container_names = ""
    for container in containers:
        container_names += (container + "_" + pod + " ")
    container_names = container_names[:-1]
    path = pathlib.Path(__file__).parent.resolve()
    process = subprocess.Popen(
        [f'{path}/get_containers_oom_score.sh', f'-c "{container_names}"', f'-n {node}'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, _ = process.communicate()
    print(stdout.decode("utf-8"))