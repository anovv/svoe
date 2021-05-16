from configs.data_feed.cryptostore_config_builder import CryptostoreConfigBuilder

from pathlib import Path

from yaml.resolver import BaseResolver

import textwrap

import numpy
import math
import yaml

# TODO figure out prod paths
# ConfigMap
DATA_FEED_CONFIG_MAP_PATH = str(Path(__file__).parent / 'svoe_data_feed_config_map.yaml')
DATA_FEED_CONFIG_MAP_NAME = 'svoe-data-feed-config-map'

# Stateful Set
DATA_FEED_STATEFUL_SET_CONFIG_PATH = str(Path(__file__).parent / 'svoe_data_feed_stateful_set.yaml')
DATA_FEED_STATEFUL_SET_NAME = 'svoe-data-feed-stateful-set'
DATA_FEED_HEADLESS_SERVICE_NAME = 'svoe-data-feed-stateful-set-service'

# Container
DATA_FEED_CONTAINER_NAME = 'svoe-data-feed-container'
DATA_FEED_IMAGE = 'busybox' # TODO

# Init Container
DATA_FEED_INIT_CONTAINER_NAME = 'svoe-data-feed-init-container'
DATA_FEED_INIT_IMAGE = 'busybox'

# Volumes
DATA_FEED_SCRIPTS_VOLUME_NAME = 'svoe-data-feed-scripts-vol'
DATA_FEED_CONFIGS_VOLUME_NAME = 'svoe-data-feed-conf-vol'

# Pods
NUM_PODS = 10


# Kubernetes specific configs
# https://faun.pub/unique-configuration-per-pod-in-a-statefulset-1415e0c80258
class KubernetesConfigBuilder(CryptostoreConfigBuilder):

    def data_feed_stateful_set(self) -> str:
        headless_service_config = {
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {
                'name': DATA_FEED_HEADLESS_SERVICE_NAME,
                'labels': {
                    'name': DATA_FEED_HEADLESS_SERVICE_NAME,
                },
            },
            'spec': {
                'clusterIP': 'None',
                'ports': [
                    {
                        'name': 'http',
                        'port': 80,
                    },
                ],
                'selector': {
                    'name': DATA_FEED_STATEFUL_SET_NAME,
                },
            },
        }

        stateful_set_config = {
            'apiVersion': 'apps/v1',
            'kind': 'StatefulSet',
            'metadata': {
                'name': DATA_FEED_STATEFUL_SET_NAME,
                'labels': {
                    'name': DATA_FEED_STATEFUL_SET_NAME,
                },
            },
            'spec': {
                'serviceName': DATA_FEED_HEADLESS_SERVICE_NAME,
                'replicas': NUM_PODS,
                'podManagementPolicy': 'Parallel',
                'selector': {
                    'matchLabels': {
                        'name': DATA_FEED_STATEFUL_SET_NAME,
                    }
                },
                'template': {
                    'metadata': {
                        'labels': {
                            'name': DATA_FEED_STATEFUL_SET_NAME
                        },
                    },
                    'spec': {
                        'containers': [
                            {
                                'name': DATA_FEED_CONTAINER_NAME,
                                'image': DATA_FEED_IMAGE,
                                'imagePullPolicy': 'IfNotPresent',
                                'command': ['/bin/sh', '-c'],
                                'args': ['echo "Starting statefulset pod"; cat /etc/svoe/data_feed/configs/data-feed-config.yaml; while true; do sleep 600; done'],
                                'volumeMounts': [
                                    {
                                        'name': DATA_FEED_CONFIGS_VOLUME_NAME,
                                        'mountPath': self.CRYPTOSTORE_CONFIG_DIR,
                                    },
                                ]
                            },
                        ],
                        'initContainers': [
                            {
                                'name': DATA_FEED_INIT_CONTAINER_NAME,
                                'image': DATA_FEED_INIT_IMAGE,
                                'command': ['/mnt/scripts/run.sh'],
                                'volumeMounts': [
                                    {
                                        'name': DATA_FEED_SCRIPTS_VOLUME_NAME,
                                        'mountPath': '/mnt/scripts',
                                    },
                                    {
                                        'name': DATA_FEED_CONFIGS_VOLUME_NAME,
                                        'mountPath': '/mnt/data',
                                    },
                                ],
                            },
                        ],
                        'volumes': [
                            {
                                'name': DATA_FEED_SCRIPTS_VOLUME_NAME,
                                'configMap': {
                                    'name': DATA_FEED_CONFIG_MAP_NAME,
                                    'defaultMode': 0o555,
                                },
                            },
                            {
                                'name': DATA_FEED_CONFIGS_VOLUME_NAME,
                                'emptyDir': {},
                            },
                        ],
                    },
                },
            },
        }

        with open(DATA_FEED_STATEFUL_SET_CONFIG_PATH, 'w+') as outfile:
            yaml.dump_all(
                [headless_service_config, stateful_set_config],
                outfile,
                default_flow_style=False,
            )

        return DATA_FEED_STATEFUL_SET_CONFIG_PATH

    # ConfigMap containing Cryptostore configs for each pod
    # Assigned to pods using initContainer
    def data_feed_config_map(self) -> str:
        # yaml woodoo, move to separate class later
        # https://stackoverflow.com/questions/67080308/how-do-i-add-a-pipe-the-vertical-bar-into-a-yaml-file-from-python

        class AsLiteral(str):
            pass

        def represent_literal(dumper, data):
            return dumper.represent_scalar(BaseResolver.DEFAULT_SCALAR_TAG,
                                           data, style="|")
        yaml.add_representer(AsLiteral, represent_literal)

        cs_conf = self._build_kuber_cryptostore_config()

        launch_script = \
            textwrap.dedent(
                """
                #!/bin/sh
                SET_INDEX=${HOSTNAME##*-}
                echo "Starting initializing for pod $SET_INDEX"
                if [ "$SET_INDEX" = "0" ]; then
                    cp /mnt/scripts/data-feed-config-0.yaml /mnt/data/data-feed-config.yaml"""
            )

        # TODO move config name to const

        for pod in cs_conf.keys():
            if pod == 0:
                continue
            s = \
                textwrap.dedent(
                    """
                    elif [ "$SET_INDEX" = "{}" ]; then
                        cp /mnt/scripts/data-feed-config-{}.yaml /mnt/data/data-feed-config.yaml""".format(pod, pod)
                )
            launch_script += s

        launch_script += \
            textwrap.dedent(
                """
                else
                    echo "Invalid stateful set index"
                    exit 1
                fi"""
            )

        config = {
            'apiVersion': 'v1',
            'kind': 'ConfigMap',
            'metadata': {
                'name': DATA_FEED_CONFIG_MAP_NAME
            },
            'data': {
                'run.sh': AsLiteral(launch_script.strip())
            }
        }

        for pod in cs_conf.keys():
            key = 'data-feed-config-' + str(pod) + '.yaml'
            config['data'][key] = AsLiteral(yaml.dump(cs_conf[pod]))

        return self._dump_yaml_config(config, DATA_FEED_CONFIG_MAP_PATH)

    # Maps pods to their cryptostore configs
    def _build_kuber_cryptostore_config(self) -> dict[int, dict]:
        config = {}
        pods_to_pairs = self._kuber_pods_to_pairs()
        for pod in pods_to_pairs.keys():
            ex_to_pairs = pods_to_pairs[pod]
            config[pod] = self._build_cryptostore_config(ex_to_pairs)
        return config

    def _kuber_pods_to_pairs(self) -> dict[int, dict[str, list[str]]]:

        # e1: p1 p2 p3 p4 p5 p6  | pairs: 6 cost: 3.6 round: 3
        #
        # e2: p1 p2 | pairs: 2 cost: 1.2 round: 1
        #
        # e3: p1 | pairs: 1 cost: 0.6 round: 1
        #
        # e4: p1 | pairs: 1 cost: 0.6 round: 1
        #
        # num_pods = 6

        num_pods = NUM_PODS
        pods = [*range(0, num_pods)]
        num_exchanges = len(self.exchanges_config)
        num_pairs = sum(len(val[0]) for val in self.exchanges_config.values())

        if num_pairs < num_pods:
            raise Exception('Can not have more pods: [{}] then pairs: [{}]'.format(num_pods, num_pairs))

        if num_pods > num_exchanges:
            # assign pods to exchanges
            ex_to_pods = {}

            # calc how many pods on average we need for a pair
            pods_per_pair = num_pods/num_pairs

            # distribute pods for each exchage
            for ex in self.exchanges_config.keys():
                pods_needed = pods_per_pair * len(self.exchanges_config[ex][0])

                # round down, distribute leftovers later
                round = math.floor(pods_needed)

                # exchange needs only 1 pod
                if round == 0 :
                    round = 1

                ex_to_pods[ex] = []
                while round > 0:
                    ex_to_pods[ex].append(pods.pop(0))
                    round -= 1

            # round robin leftovers
            while len(pods) > 0:
                # find exchange with largest residual of needed capacity and assign a pod
                _max = max(ex_to_pods.items(), key = lambda x: pods_per_pair * len(self.exchanges_config[x[0]][0]) - len(ex_to_pods[x[0]]))
                ex_to_pods[_max[0]].append(pods.pop(0))

            # distribute pairs to pods
            pods_to_pairs = {}
            for ex in ex_to_pods.keys():
                pairs = self.exchanges_config[ex][0]
                assigned_pods = ex_to_pods[ex]
                split = numpy.array_split(pairs, len(assigned_pods))
                for i in range(len(assigned_pods)):
                    ex_to_pairs = {}
                    ex_to_pairs[ex] = split[i].tolist()
                    pods_to_pairs[assigned_pods[i]] = ex_to_pairs

            return pods_to_pairs

        else:
            ex_pairs_tuple_list = []
            for ex in self.exchanges_config.keys():
                pairs = self.exchanges_config[ex][0]
                for pair in pairs:
                    ex_pairs_tuple_list.append((ex,pair))

            split = numpy.array_split(ex_pairs_tuple_list, num_pods)

            # distribute pairs to pods
            pods_to_pairs = {}
            for i in range(num_pods):
                pod = pods[i]
                pods_to_pairs[pod] = {}
                for ex_pair_tuple in split[i].tolist():
                    ex = ex_pair_tuple[0]
                    pair = ex_pair_tuple[1]
                    if ex in pods_to_pairs[pod]:
                        pods_to_pairs[pod][ex].append(pair)
                    else:
                        pods_to_pairs[pod][ex] = [pair]

            return pods_to_pairs
