# cluster should have kube-prometheus-stack, metrics-server, metrics-server-exporter and data-feed
# CLUSTER = 'k8s.vpc-apse1.dev.svoe.link'
CLUSTER = 'minikube-1'
DATA_FEED_NAMESPACE = 'data-feed'
DATA_FEED_CONTAINER = 'data-feed-container'
DATA_FEED_CM_CONFIG_NAME = 'data-feed-config.yaml'
REDIS_CONTAINER = 'redis'
NODE_MEMORY_ALLOC_THRESHOLD = 0.75 # do not schedule pods onto node if memory usage is above this
NODE_RESCHEDULE_PERIOD = 10 # how long to wait for current pod to run until scheduling next pod
RUN_ESTIMATION_FOR = 120 # how long to run estimation
PROM_NAMESPACE = 'monitoring'
PROM_POD_NAME = 'prometheus-kube-prometheus-stack-prometheus-0'
PROM_PORT_FORWARD = '9090'
PROM = f'http://localhost:{PROM_PORT_FORWARD}'
