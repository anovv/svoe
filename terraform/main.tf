# TODO move tfstate to S3 bucket
# TODO move shared variables to .tfvars

provider "aws" {
  region                  = "ap-northeast-1"
  shared_credentials_file = "~/.aws/credentials"
  profile                 = "default"
}

module "glue" {
  source = "./modules/aws/glue"
}

module "apn1_vpc" {
  source                 = "./modules/aws/vpc"
  name                   = "apn1-vpc"
  cidr                   = "10.0.0.0/16"
  azs                    = ["ap-northeast-1a"]
  private_subnets        = []
  public_subnets         = ["10.0.101.0/24"]
  environment            = "dev"
  enable_nat_gateway     = false
  single_nat_gateway     = false
  one_nat_gateway_per_az = false
  cluster_name           = "apn1.k8s.local"
}

module "apn1_kops_resources" {

  source      = "./modules/aws/kops_resources"
  environment = "dev"
  ingress_ips = ["10.0.0.0/16"]
  vpc_id      = module.apn1_vpc.vpc_id
}