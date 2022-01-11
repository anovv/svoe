# TODO move tfstate to S3 bucket
# TODO move shared variables to .tfvars

provider "aws" {
  region                  = var.region
  shared_credentials_file = "~/.aws/credentials"
  profile                 = "default"
}

locals {
  cluster_name = "${var.cluster_name_prefix}.${var.environment}.${var.domain}"
}

module "glue" {
  source = "./modules/aws/glue"
}

module "apn1_vpc" {
  source                 = "./modules/aws/vpc"
  name                   = var.vpc_name
  cidr                   = var.cidr
  azs                    = var.azs
  private_subnets        = var.private_subnets
  public_subnets         = var.public_subnets
  environment            = var.environment
  enable_nat_gateway     = false
  single_nat_gateway     = false
  one_nat_gateway_per_az = false
  cluster_name           = local.cluster_name
}

module "kops_resources" {

  source      = "./modules/aws/kops_resources"
  environment = var.environment
  domain = var.domain
#  ingress_ips = var.ingress_ips
}