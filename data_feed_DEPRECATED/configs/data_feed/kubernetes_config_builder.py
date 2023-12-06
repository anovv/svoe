from data_feed.configs.data_feed.cryptostore_config_builder import CryptostoreConfigBuilder

from pathlib import Path

from yaml.resolver import BaseResolver

import textwrap

import numpy
import math
import yaml

# TODO figure out prod paths
# ConfigMap
CONFIG_MAP_GEN_PATH = str(Path(__file__).parent / 'svoe_data_feed_config_map.yaml')
CONFIG_MAP_NAME_PREFIX = 'svoe-data-feed-cm'

# Stateful Set
STATEFUL_SET_GEN_PATH = str(Path(__file__).parent / 'svoe_data_feed_stateful_set.yaml')
STATEFUL_SET_NAME_REFIX = 'svoe-data-feed-ss'
SERVICE_NAME_REFIX = 'svoe-data-feed-ss-svc'

# Container
CONTAINER_NAME = 'svoe-data-feed-container'
IMAGE = '050011372339.dkr.ecr.ap-northeast-1.amazonaws.com/anov/svoe_data_feed:v7'

# TODO this should be in sync with data feed service
CONFIG_DIR = '/etc/svoe/data_feed/configs'
# TODO use this instead of hardcoding
CONFIG_FILE_NAME = 'data-feed-config.yaml'

# Init Container
INIT_CONTAINER_NAME = 'svoe-data-feed-init-container'
INIT_IMAGE = 'busybox'

# Volumes
SCRIPTS_VOLUME_NAME_PREFIX = 'svoe-data-feed-scripts-vol'
CONFIGS_VOLUME_NAME_PREFIX = 'svoe-data-feed-conf-vol'

# TODO add namespace

# Kubernetes specific configs
# https://faun.pub/unique-configuration-per-pod-in-a-statefulset-1415e0c80258
class KubernetesConfigBuilder(CryptostoreConfigBuilder):

    def gen(self) -> tuple[str, str]:
        config_map_specs = []
        service_set_specs = [] # [headless_service_config, stateful_set_config]

        for exchange in self.exchanges_config.keys():
            for instrument in self.exchanges_config[exchange].keys():

                config_map_name = (exchange + '-' + instrument + '-' + CONFIG_MAP_NAME_PREFIX).replace('_', '-').lower()
                stateful_set_name = (exchange + '-' + instrument + '-' + STATEFUL_SET_NAME_REFIX).replace('_', '-').lower()
                service_name = (exchange + '-' + instrument + '-' + SERVICE_NAME_REFIX).replace('_', '-').lower()
                configs_volume_name = (exchange + '-' + instrument + '-' + CONFIGS_VOLUME_NAME_PREFIX).replace('_', '-').lower()
                scripts_volume_name = (exchange + '-' + instrument + '-' + SCRIPTS_VOLUME_NAME_PREFIX).replace('_', '-').lower()

                config_map_spec = self._config_map(
                    config_map_name,
                    exchange,
                    instrument,
                )
                config_map_specs.append(config_map_spec)

                service_and_stateful_set_specs = self._service_and_stateful_set(
                    service_name,
                    stateful_set_name,
                    configs_volume_name,
                    scripts_volume_name,
                    config_map_name,
                )

                service_set_specs.extend(list(service_and_stateful_set_specs))

        with open(CONFIG_MAP_GEN_PATH, 'w+') as outfile:
            yaml.dump_all(
                config_map_specs,
                outfile,
                default_flow_style=False,
            )

        with open(STATEFUL_SET_GEN_PATH, 'w+') as outfile:
            yaml.dump_all(
                service_set_specs,
                outfile,
                default_flow_style=False,
            )

        # TODO put all in one file?
        return CONFIG_MAP_GEN_PATH, STATEFUL_SET_GEN_PATH

    def _service_and_stateful_set(
        self,
        service_name: str,
        stateful_set_name: str,
        configs_volume_name: str,
        scripts_volume_name: str,
        config_map_name: str,
    ) -> tuple[dict, dict]:
        service_spec = {
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {
                'name': service_name,
                'labels': {
                    'name': service_name,
                    'monitored': 'all',
                },
            },
            'spec': {
                'clusterIP': 'None',
                'ports': [
                    {
                        # is this needed ?
                        'name': 'http',
                        'port': 80,
                    },
                    {
                        'name': 'redis',
                        'port': 6379,
                        'targetPort': 6379,
                        'protocol': 'TCP',
                    },
                    {
                        'name': 'redis-metrics',
                        'port': 9121,
                        'targetPort': 9121,
                        'protocol': 'TCP',
                    }
                ],
                'selector': {
                    'name': stateful_set_name,
                },
            },
        }

        stateful_set_spec = {
            'apiVersion': 'apps/v1',
            'kind': 'StatefulSet',
            'metadata': {
                'name': stateful_set_name,
                'labels': {
                    'name': stateful_set_name,
                },
            },
            'spec': {
                'serviceName': service_name,
                'replicas': 0,
                'selector': {
                    'matchLabels': {
                        'name': stateful_set_name,
                    }
                },
                'template': {
                    'metadata': {
                        'labels': {
                            'name': stateful_set_name
                        },
                    },
                    'spec': {
                        'containers': [
                            {
                                'name': 'redis',
                                'image': 'redis:alpine',
                                'ports': [
                                    {
                                        'containerPort': 6379, # TODO use const
                                    }
                                ],
                                # 'resources': {
                                #     'requests': {
                                #         'cpu': '20m',
                                #         'memory': '30Mi',
                                #     }
                                # },
                            },
                            {
                                'name': 'redis-exporter',
                                'image': 'oliver006/redis_exporter:latest',
                                'ports': [
                                    {
                                        'containerPort': 9121, # TODO use const
                                        'name': 'redis-metrics'
                                    }
                                ],
                            },
                            {
                                'name': CONTAINER_NAME,
                                'image': IMAGE,
                                'imagePullPolicy': 'IfNotPresent',
                                'volumeMounts': [
                                    {
                                        'name': configs_volume_name,
                                        'mountPath': CONFIG_DIR,
                                    },

                                ],
                                # 'resources': {
                                #     'requests': {
                                #         'cpu': '200m',
                                #         'memory': '200Mi',
                                #     }
                                # },
                                # TODO fix livenessProbe
                                # 'livenessProbe': {
                                #     'exec': {
                                #         'command': [
                                #             'python',
                                #             'health_check/health_check.py',
                                #         ],
                                #     },
                                #     'initialDelaySeconds': 60,
                                #     'periodSeconds': 5,
                                # },
                                # 'resources': {
                                #     'requests': {
                                #         'cpu': '450m',
                                #         'memory': '250Mi',
                                #     }
                                # },
                            },
                        ],
                        'initContainers': [
                            {
                                'name': INIT_CONTAINER_NAME,
                                'image': INIT_IMAGE,
                                'command': ['/mnt/scripts/run.sh'],
                                'volumeMounts': [
                                    {
                                        'name': scripts_volume_name,
                                        'mountPath': '/mnt/scripts',
                                    },
                                    {
                                        'name': configs_volume_name,
                                        'mountPath': '/mnt/data',
                                    },
                                ],
                            },
                        ],
                        'volumes': [
                            {
                                'name': scripts_volume_name,
                                'configMap': {
                                    'name': config_map_name,
                                    'defaultMode': 0o555,
                                },
                            },
                            {
                                'name': configs_volume_name,
                                'emptyDir': {},
                            },
                        ],
                    },
                },
            },
        }

        return service_spec, stateful_set_spec

    # ConfigMap containing Cryptostore configs for each pod
    # Assigned to pods using initContainer
    def _config_map(
        self,
        name: str,
        exchange: str,
        instrument: str,
    ) -> dict:
        # yaml woodoo, move to separate class later
        # https://stackoverflow.com/questions/67080308/how-do-i-add-a-pipe-the-vertical-bar-into-a-yaml-file-from-python

        class AsLiteral(str):
            pass

        def represent_literal(dumper, data):
            return dumper.represent_scalar(BaseResolver.DEFAULT_SCALAR_TAG,
                                           data, style="|")
        yaml.add_representer(AsLiteral, represent_literal)

        pod_config_mapping = self._kuber_cryptostore_mapping(exchange, instrument)

        # TODO move 'data-feed-config' to const in cryptofeed_config_builder
        launch_script = \
            textwrap.dedent(
                """
                #!/bin/sh
                SET_INDEX=${HOSTNAME##*-}
                echo "Starting initializing for pod $SET_INDEX"
                if [ "$SET_INDEX" = "0" ]; then
                    cp /mnt/scripts/data-feed-config-0.yaml /mnt/data/data-feed-config.yaml"""
            )

        for pod in pod_config_mapping.keys():
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
                'name': name,
            },
            'data': {
                'run.sh': AsLiteral(launch_script.strip())
            }
        }

        for pod in pod_config_mapping.keys():
            key = 'data-feed-config-' + str(pod) + '.yaml'
            config['data'][key] = AsLiteral(yaml.dump(pod_config_mapping[pod]))

        return config

    # Maps pods to their cryptostore configs
    def _kuber_cryptostore_mapping(
        self,
        exchange: str,
        instrument: str,
    ) -> dict[int, dict]:
        symbols = self.exchanges_config[exchange][instrument][0]
        symbols_per_pod = self.exchanges_config[exchange][instrument][3]
        pods_count = math.ceil(len(symbols)/symbols_per_pod)

        config = {}
        for pod in range(pods_count):
            symbols_for_pod = symbols[symbols_per_pod*pod:min(len(symbols), symbols_per_pod*(pod + 1))]
            config[pod] = self._cryptostore_config(exchange, instrument, symbols_for_pod)
        return config

### --------------------------------------------

    def _kuber_pods_to_pairs_DEPRECATED(self) -> dict[int, dict[str, list[str]]]:

        # e1: p1 p2 p3 p4 p5 p6  | pairs: 6 cost: 3.6 round: 3
        #
        # e2: p1 p2 | pairs: 2 cost: 1.2 round: 1
        #
        # e3: p1 | pairs: 1 cost: 0.6 round: 1
        #
        # e4: p1 | pairs: 1 cost: 0.6 round: 1
        #
        # num_pods = 6

        num_pods = 10
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
