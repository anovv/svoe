# cluster should have kube-prometheus-stack, metrics-server, metrics-server-exporter and data-feed
CLUSTER = 'k8s.vpc-apne1.dev.svoe.link'
# CLUSTER = 'minikube-1'

DATA_FEED_NAMESPACE = 'data-feed'
DATA_FEED_CONTAINER = 'data-feed-container'
DATA_FEED_CM_CONFIG_NAME = 'data-feed-config.yaml'

REDIS_CONTAINER = 'redis'
REDIS_EXPORTER_CONTAINER = 'redis-exporter'

NODE_MEMORY_ALLOC_THRESHOLD = 0.6 # do not schedule pods onto node if memory usage is above this
NODE_NEXT_SCHEDULE_PERIOD = 20 # how long to wait for current pod to run until scheduling next pod

RUN_ESTIMATION_FOR = 180 # how long to run estimation

PROM_NAMESPACE = 'monitoring'
PROM_POD_NAME = 'prometheus-kube-prometheus-stack-prometheus-0'
PROM_PORT_FORWARD = '9090'
# PROM = f'http://localhost:{PROM_PORT_FORWARD}'
PROM = 'http://prometheus.k8s.vpc-apne1.dev.svoe.link:30001'

REMOTE_SCRIPTS_DS_CONTAINER = 'remote-scripts-runner'
REMOTE_SCRIPTS_DS_NAMESPACE = 'kube-system'
REMOTE_SCRIPTS_DS_LABEL_SELECTOR = 'app=remote-scripts'

BULK_SCHEDULE_SIZE = 2 # number of simultaneously scheduled pods on a node without checking resourcess
