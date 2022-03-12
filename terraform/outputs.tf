# TODO pipe more vars from all modules which are used in Helmfile

output "vpc_mesh_output" {
  value = module.vpc_mesh.vpc_mesh_output
}

output "multicluster_config_output" {
  value = local.multicluster_config_output
}

output "kops_s3_bucket_name" {
  value = module.apn1_kops_resources.kops_s3_bucket_name
}

output "kops_hosted_zone_name_servers" {
  value = module.apn1_kops_resources.kops_hosted_zone_name_servers
}

output "ecr_repo_name" {
  value = module.ecr.ecr_repo_name
}

output "ecr_repo_registry_id" {
  value = module.ecr.ecr_repo_registry_id
}

output "ecr_repo_url" {
  value = module.ecr.ecr_repo_url
}