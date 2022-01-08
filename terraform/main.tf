# TODO move tfstate to S3 bucket
# TODO move shared variables to .tfvars

provider "aws" {
  region                  = var.region
  shared_credentials_file = "~/.aws/credentials"
  profile                 = "default"
}

module "glue" {
  source = "./modules/aws/glue"
}

module "apn1_vpc" {
  source                 = "./modules/aws/vpc"
  name                   = "apn1-vpc"
  cidr                   = var.cidr
  azs                    = var.azs
  private_subnets        = var.private_subnets
  public_subnets         = var.public_subnets
  environment            = var.environment
  enable_nat_gateway     = false
  single_nat_gateway     = false
  one_nat_gateway_per_az = false
  cluster_name           = var.cluster_name
}

module "apn1_kops_resources" {

  source      = "./modules/aws/kops_resources"
  environment = var.environment
  ingress_ips = var.ingress_ips
  vpc_id      = module.apn1_vpc.vpc_id
}