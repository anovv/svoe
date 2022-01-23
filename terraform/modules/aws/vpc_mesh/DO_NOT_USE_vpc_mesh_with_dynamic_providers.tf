## TODO Terraform does not support dynamic provider config
## Hence we need a script to generate terraform configs in json (see gen_terraform_vpc_mesh_json.py)
## Once support is added, the code bellow can be used
#

#data "aws_caller_identity" "current" {}

#provider "aws" {
#  region                  = "ap-northeast-1"
#  shared_credentials_file = "~/.aws/credentials"
#  alias = "ap-northeast-1"
#}

#data "aws_caller_identity" "current" {
#  provider = aws.ap-northeast-1
#}

#provider "aws" {
#  region                  = "ap-southeast-1"
#  shared_credentials_file = "~/.aws/credentials"
#  alias = "ap-southeast-1"
#}
#
#module "vpcs" {
#  source = "./vpcs"
#}
#
#data "aws_route_tables" "test" {
#  vpc_id = module.vpcs.vpc-apne1-vpc_id
#  provider = aws.ap-northeast-1
##  depends_on = [module.vpcs]
#}
#
### set up full mesh peering here
### e.g. https://github.com/grem11n/terraform-aws-vpc-peering/tree/v4.0.1/examples/single-account-multi-region
##
##provider "aws" {
##  for_each                = var.vpc_mesh_config
##  region                  = each.value.region
##  shared_credentials_file = "~/.aws/credentials"
##}
##
##module "vpc" {
##  source                 = "../vpc"
##  for_each               = var.vpc_mesh_config
##  name                   = each.key
##  cidr                   = each.value.cidr
##  azs                    = each.value.azs
##  private_subnets        = each.value.private_subnets
##  public_subnets         = each.value.public_subnets
##  enable_nat_gateway     = each.value.enable_nat_gateway
##  single_nat_gateway     = each.value.single_nat_gateway
##  one_nat_gateway_per_az = each.value.single_nat_gateway
##
##  provider = aws[each.key]
##}
##
##locals {
##  vpc_pairs = toset([
##    for pair in setproduct(keys(var.vpc_mesh_config), keys(var.vpc_mesh_config)) : pair
##    if pair[0] != pair[1]
##  ])
##}
##

#resource "aws_vpc_peering_connection" "requester" {
#  for_each    = local.vpc_pairs
#  provider    = aws[each.value[0]]
#  vpc_id      = module.vpc[each.value[0]].vpc_id
#  peer_vpc_id = module.vpc[each.value[1]].vpc_id
#  peer_region = var.vpc_mesh_config[each.value[1]].region

#  provider = aws.ap-northeast-1
#  vpc_id = module.vpcs.vpc-apne1-vpc_id
#  peer_vpc_id = module.vpcs.vpc-apse1-vpc_id
#  peer_region = "ap-southeast-1"
#  peer_owner_id = "${data.aws_caller_identity.current.account_id}"
#  auto_accept = false

#  tags = {
#    Side = "Requester"
#  }
#
#  timeouts {
#    create = "10m"
#    delete = "10m"
#  }

#  accepter {
#    allow_remote_vpc_dns_resolution  = true
#    allow_classic_link_to_remote_vpc = true
#    allow_vpc_to_remote_classic_link = true
#  }
#
#  requester {
#    allow_remote_vpc_dns_resolution  = true
#    allow_classic_link_to_remote_vpc = true
#    allow_vpc_to_remote_classic_link = true
#  }
#}
##
#resource "aws_vpc_peering_connection_accepter" "accepter" {
#  for_each                  = local.vpc_pairs
#  provider                  = aws[each.value[1]]
#  vpc_peering_connection_id = aws_vpc_peering_connection.requester[each.key].id
#  auto_accept               = true

#  vpc_peering_connection_id = aws_vpc_peering_connection.requester.id
#  provider = aws.ap-southeast-1
#  auto_accept = true
#
#  tags = {
#    Side = "Accepter"
#  }

#  accepter {
#    allow_remote_vpc_dns_resolution  = true
#    allow_classic_link_to_remote_vpc = true
#    allow_vpc_to_remote_classic_link = true
#  }
#
#  requester {
#    allow_remote_vpc_dns_resolution  = true
#    allow_classic_link_to_remote_vpc = true
#    allow_vpc_to_remote_classic_link = true
#  }
#}

#resource "aws_vpc_peering_connection_options" "requester" {
#  provider = aws.ap-northeast-1
#
#  # As options can't be set until the connection has been accepted
#  # create an explicit dependency on the accepter.
#  vpc_peering_connection_id = aws_vpc_peering_connection_accepter.accepter.id
#
#  requester {
#    allow_remote_vpc_dns_resolution  = true
#    allow_classic_link_to_remote_vpc = true
#    allow_vpc_to_remote_classic_link = true
#  }
#}
#
#resource "aws_vpc_peering_connection_options" "accepter" {
#  provider = aws.ap-southeast-1
#
#  vpc_peering_connection_id = aws_vpc_peering_connection_accepter.accepter.id
#
#  accepter {
#    allow_remote_vpc_dns_resolution  = true
#    allow_classic_link_to_remote_vpc = true
#    allow_vpc_to_remote_classic_link = true
#  }
#}

##
### Routes
##data "aws_route_tables" "route_tables" {
##  for_each = var.vpc_mesh_config
##  provider = aws[each.key]
##  vpc_id   = module.vpc[each.key].vpc_id
##}
##
##locals {
##  requester_to_accepter_routes = flatten([
##    for vpc_pair in local.vpc_pairs : [
##      for route_table_id in data.aws_route_tables.route_tables[vpc_pair[0]].ids : {
##        provider                  = aws[vpc_pair[0]]
##        route_table_id            = route_table_id
##        destination_cidr_block    = module.vpc[vpc_pair[1]].vpc_cidr_block
##        vpc_peering_connection_id = aws_vpc_peering_connection.requester[index(local.vpc_pairs, vpc_pair)].id
##      }
##    ]
##  ])
##
##  accepter_to_requester_routes = flatten([
##    for vpc_pair in local.vpc_pairs : [
##      for route_table_id in data.aws_route_tables.route_tables[vpc_pair[1]].ids : {
##        provider                  = aws[vpc_pair[1]]
##        route_table_id            = route_table_id
##        destination_cidr_block    = module.vpc[vpc_pair[0]].vpc_cidr_block
##        vpc_peering_connection_id = aws_vpc_peering_connection.requester[index(local.vpc_pairs, vpc_pair)].id
##      }
##    ]
##  ])
##}
##
##resource "aws_route" "requester_routes" {
##  for_each                  = local.requester_to_accepter_routes
##  provider                  = each.value.provider
##  route_table_id            = each.value.route_table_id
##  destination_cidr_block    = each.value.destination_cidr_block
##  vpc_peering_connection_id = each.value.vpc_peering_connection_id
##}
##
##resource "aws_route" "accepter_routes" {
##  for_each                  = local.accepter_to_requester_routes
##  provider                  = each.value.provider
##  route_table_id            = each.value.route_table_id
##  destination_cidr_block    = each.value.destination_cidr_block
##  vpc_peering_connection_id = each.value.vpc_peering_connection_id
##}
#
##output "vpc_mesh_output" {
##  value = {
##    for vpc_key in keys(var.vpc_mesh_config):
##      vpc_key => module.vpc[vpc_key]
##  }
##}
#
##variable "vpc_mesh_config" {
##  type = "map"
##  description = "Global configuration for VPC mesh"
##}