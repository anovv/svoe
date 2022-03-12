# TODO move tfstate to S3 bucket

provider "aws" {
  # This is a dummy provider needed for terraform to compile
  region = "ap-northeast-1"
}

module "glue" {
  source = "./modules/aws/glue"
}

module "vpc_mesh" {
  source = "./modules/aws/vpc_mesh"
}

module "apn1_kops_resources" {
  source              = "./modules/aws/kops_resources"
  kops_s3_bucket_name = var.kops_s3_bucket_name
  domain              = var.domain
}

module "ecr" {
  source = "./modules/aws/ecr"
  ecr_repo_name = var.ecr_repo_name
}

# TODO move everything below to a multicluster module
locals {
  multicluster_config_output = {
    for cluster in var.multicluster_config:
      cluster["cluster_id"] => merge({
          cluster_name: join(".", [cluster["name_prefix"], cluster["vpc_name"], cluster["environment"], var.domain])
          kops_s3_bucket_name: var.kops_s3_bucket_name
        },{
          for k, v in cluster:
            k => v
        },{
          for k, v in module.vpc_mesh.vpc_mesh_output[cluster["vpc_name"]]:
            k => v
        })
  }
}
