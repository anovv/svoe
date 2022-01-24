import json
from itertools import combinations
from enum import Enum

input_config = {}
PATH_TO_INPUT = 'terraform.tfvars.json'

# VPCS
# Providers
providers = {}
# VPC modules
vpcs = {}
# Outputs
vpcs_output = {}


class vpc_output_values(str, Enum):
    VPC_ID = 'vpc_id'
    VPC_CIDR_BLOCK = 'vpc_cidr_block'
    PUBLIC_SUBNETS = 'public_subnets'
    PRIVATE_SUBNETS = 'private_subnets'
    AZS = 'azs'
    DEFAULT_SECURITY_GROUP_ID = 'default_security_group_id'
    NATGW_IDS = 'natgw_ids'


# Mesh connections
# Route tables
route_tables_data = {}
# VPC peering connections
peerings = []
# VPC peering options
peering_options = []
# Routes to peer cidr
routes = []
vpc_mesh_output = {}
# Security groups
security_groups = {}


def get_vpcs_module_output(vpc_name, output_name):
    return '${module.vpcs.vpcs_output[\"' + vpc_name + '\"][\"' + output_name + '\"]}'


def get_provider(vpc_name):
    return 'aws.' + providers[vpc_name]['provider']['aws']['alias']


def get_peering_connection(vpc_name_requester, vpc_name_accepter):
    return 'r-' + vpc_name_requester + '-to-' + vpc_name_accepter


def get_peering_connection_accepter(vpc_name):
    return 'a-' + vpc_name


def get_region(vpc_name):
    return input_config[vpc_name]['region']


def get_route_tables(vpc_name):
    return 'rts-' + vpc_name

def get_common_sg(vpc_name):
    return 'common-' + vpc_name

def get_routes(vpc_name_requester, vpc_name_accepter):
    return 'routes-' + vpc_name_requester + '-to-' + vpc_name_accepter


with open(PATH_TO_INPUT) as json_file:
    input = json.load(json_file)
    input_config = input['vpc_mesh_config']['vpcs']

    vpcs_output['output'] = {'vpcs_output': {'value': {}}}
    for vpc_name in input_config:
        providers[vpc_name] = {
            'provider': {
                'aws': {
                    'region': get_region(vpc_name),
                    'shared_credentials_file': '~/.aws/credentials',
                    'alias': get_region(vpc_name)
                }
            }
        }

        # VPCs module (child module)
        vpcs[vpc_name] = {
            'module': {
                vpc_name: {
                    'source': 'terraform-aws-modules/vpc/aws',
                    'name': vpc_name,
                    'providers': {
                        'aws': get_provider(vpc_name),
                    }
                }
            }
        }

        # populate VPCs modules vars
        inputs_to_skip = ['region'] # TODO
        for k in input_config[vpc_name]:
            if k in inputs_to_skip:
                continue
            vpcs[vpc_name]['module'][vpc_name][k] = input_config[vpc_name][k]

        vpcs_output['output']['vpcs_output']['value'][vpc_name] = dict([
            (output_value, '${module.' + vpc_name + '.' + output_value + '}')
            for output_value in vpc_output_values
        ])
        vpcs_output['output']['vpcs_output']['value'][vpc_name]['region'] = get_region(vpc_name)

        route_tables_data[vpc_name] = {
            'data': {
                'aws_route_tables': {
                    get_route_tables(vpc_name): {
                        'vpc_id': get_vpcs_module_output(vpc_name, vpc_output_values.VPC_ID),
                        'provider': get_provider(vpc_name),
                    }
                }
            }
        }

        security_groups[vpc_name] = {
            'resource': {
                'aws_security_group': {
                    get_common_sg(vpc_name): {
                        'name': get_common_sg(vpc_name),
                        'vpc_id': get_vpcs_module_output(vpc_name, vpc_output_values.VPC_ID),
                        'ingress': [
                            {
                                'description': 'Connectivity test',
                                'from_port': 0,
                                'protocol': -1, # TODO figure out security group rules and ports to open
                                'to_port': 0,
                                'cidr_blocks': ["0.0.0.0/0"], # TODO use vpc_cidrs

                                # Below fields are only needed for compile
                                'ipv6_cidr_blocks': [],
                                'prefix_list_ids': [],
                                'security_groups': [],
                                'self': False
                            },
                            # {
                            #     'description': 'Cilium etcd',
                            #     'from_port': 2379, # TODO this is duplicate??
                            #     'protocol': 'tcp',
                            #     'to_port': 2379,
                            #     'cidr_blocks': ["0.0.0.0/0"],  # TODO use vpc_cidrs
                            #
                            #     # Below fields are only needed for compile
                            #     'ipv6_cidr_blocks': [],
                            #     'prefix_list_ids': [],
                            #     'security_groups': [],
                            #     'self': False
                            # },
                        ],
                        'provider': get_provider(vpc_name)
                    }
                }
            }
        }

    vpc_pairs = [p for p in combinations(input_config.keys(), 2)]

    for vpc_pair in vpc_pairs:
        peerings.append({
            'resource': {
                'aws_vpc_peering_connection': {
                    get_peering_connection(vpc_pair[0], vpc_pair[1]): {
                        'provider': get_provider(vpc_pair[0]),
                        'vpc_id': get_vpcs_module_output(vpc_pair[0], vpc_output_values.VPC_ID),
                        'peer_vpc_id': get_vpcs_module_output(vpc_pair[1], vpc_output_values.VPC_ID),
                        'peer_region': get_region(vpc_pair[1]),
                        'tags': {
                            'Side': 'Requester',
                        },
                        'timeouts': {
                            'create': '10m',
                            'delete': '10m'
                        }
                    }
                }
            }
        })

        # Peering connection accepters
        peerings.append({
            'resource': {
                'aws_vpc_peering_connection_accepter': {
                    get_peering_connection_accepter(vpc_pair[1]): {
                        'provider': get_provider(vpc_pair[1]),
                        'vpc_peering_connection_id': '${aws_vpc_peering_connection.' + get_peering_connection(
                            vpc_pair[0],
                            vpc_pair[
                                1]) + '.id}',
                        'auto_accept': True,
                        'tags': {
                            'Side': 'Accepter',
                        }
                    }
                }
            }
        })

        peering_options.extend([
            {
                'resource': {
                    'aws_vpc_peering_connection_options': {
                        get_peering_connection(vpc_pair[0], vpc_pair[1]): {
                            'provider': get_provider(vpc_pair[0]),
                            'vpc_peering_connection_id': '${aws_vpc_peering_connection_accepter.' + get_peering_connection_accepter(
                                vpc_pair[1]) + '.id}',
                            'requester': {
                                'allow_remote_vpc_dns_resolution': True,  # TODO
                                'allow_classic_link_to_remote_vpc': True,
                                'allow_vpc_to_remote_classic_link': True,
                            },
                        }
                    }
                }
            },
            {
                'resource': {
                    'aws_vpc_peering_connection_options': {
                        get_peering_connection_accepter(vpc_pair[1]): {
                            'provider': get_provider(vpc_pair[1]),
                            'vpc_peering_connection_id': '${aws_vpc_peering_connection_accepter.' + get_peering_connection_accepter(
                                vpc_pair[1]) + '.id}',
                            'accepter': {
                                'allow_remote_vpc_dns_resolution': True,  # TODO
                                'allow_classic_link_to_remote_vpc': True,
                                'allow_vpc_to_remote_classic_link': True,
                            },
                        }
                    }
                }
            }])

        routes.extend([{
            'resource': {
                'aws_route': {
                    get_routes(vpc_pair[0], vpc_pair[1]): {
                        'count': '${length(data.aws_route_tables.' + get_route_tables(vpc_pair[0]) + '.ids)}',
                        'route_table_id': '${tolist(data.aws_route_tables.' + get_route_tables(
                            vpc_pair[0]) + '.ids)[count.index]}',
                        'provider': get_provider(vpc_pair[0]),
                        'destination_cidr_block': get_vpcs_module_output(vpc_pair[1], vpc_output_values.VPC_CIDR_BLOCK),
                        'vpc_peering_connection_id': '${aws_vpc_peering_connection.' + get_peering_connection(
                            vpc_pair[0],
                            vpc_pair[
                                1]) + '.id}'
                    }
                }
            }
        }, {
            'resource': {
                'aws_route': {
                    get_routes(vpc_pair[1], vpc_pair[0]): {
                        'count': '${length(data.aws_route_tables.' + get_route_tables(vpc_pair[1]) + '.ids)}',
                        'route_table_id': '${tolist(data.aws_route_tables.' + get_route_tables(
                            vpc_pair[1]) + '.ids)[count.index]}',
                        'provider': get_provider(vpc_pair[1]),
                        'destination_cidr_block': get_vpcs_module_output(vpc_pair[0], vpc_output_values.VPC_CIDR_BLOCK),
                        'vpc_peering_connection_id': '${aws_vpc_peering_connection.' + get_peering_connection(
                            vpc_pair[0],
                            vpc_pair[
                                1]) + '.id}'
                    }
                }
            }
        }])

    vpc_mesh_output['output'] = {'vpc_mesh_output': {'value': {}}}
    for vpc_name in input_config:
        vpc_mesh_output['output']['vpc_mesh_output']['value'][vpc_name] = dict([
            (output_value, get_vpcs_module_output(vpc_name, output_value))
            for output_value in vpc_output_values
        ])
        vpc_mesh_output['output']['vpc_mesh_output']['value'][vpc_name]['region'] = get_region(vpc_name)
        vpc_mesh_output['output']['vpc_mesh_output']['value'][vpc_name]['security_group_override'] = '${aws_security_group.' + get_common_sg(vpc_name) + '.id}'

# VPCs module
config_vpcs = []
for k in providers:
    config_vpcs.append(providers[k])

for k in vpcs:
    config_vpcs.append(vpcs[k])

config_vpcs.append(vpcs_output)

json_config_vpcs = json.dumps(config_vpcs, indent=2)
with open('modules/aws/vpc_mesh/vpcs/vpcs.tf.json', 'w') as outfile:  # separate child module
    outfile.write(json_config_vpcs)

# VPCs module with full mesh
config_vpc_mesh = []
for k in providers:
    config_vpc_mesh.append(providers[k])

config_vpc_mesh.append({
    'module': {
        'vpcs': {
            'source': './vpcs',
        }
    }
})

for k in route_tables_data:
    config_vpc_mesh.append(route_tables_data[k])

for k in security_groups:
    config_vpc_mesh.append(security_groups[k])

for v in peerings:
    config_vpc_mesh.append(v)

for v in peering_options:
    config_vpc_mesh.append(v)

for v in routes:
    config_vpc_mesh.append(v)

config_vpc_mesh.append(vpc_mesh_output)

json_config_vpc_mesh = json.dumps(config_vpc_mesh, indent=2)
with open('modules/aws/vpc_mesh/vpcs_with_mesh_connections.tf.json', 'w') as outfile:  # composite parent module
    outfile.write(json_config_vpc_mesh)
