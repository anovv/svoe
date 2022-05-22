# cluster should have kube-prometheus-stack, metrics-server, metrics-server-exporter and data-feed
# CLUSTER = 'k8s.vpc-apse1.dev.svoe.link'
CLUSTER = 'minikube-1'
DATA_FEED_NAMESPACE = 'data-feed'
DATA_FEED_CONTAINER = 'data-feed-container'
DATA_FEED_CM_CONFIG_NAME = 'data-feed-config.yaml'
REDIS_CONTAINER = 'redis'
# TODO dynamic parallelism based on heuristics
PARALLELISM = 2 # number of simultaneously running pods
ESTIMATION_RUN_DURATION = 100 # how long to run a pod
PROM_NAMESPACE = 'monitoring'
PROM_POD_NAME = 'prometheus-kube-prometheus-stack-prometheus-0'
PROM_PORT_FORWARD = '9090'
PROM = f'http://localhost:{PROM_PORT_FORWARD}'