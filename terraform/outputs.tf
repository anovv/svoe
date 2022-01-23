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