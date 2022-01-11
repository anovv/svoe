# Needed for ELB
#output "k8s_security_group_id" {
#  value = aws_security_group.k8s_security_group.id
#}

output "kops_s3_bucket_name" {
  value = aws_s3_bucket.kops_state.bucket
}

output "kops_hosted_zone_name_severs" {
  value = aws_route53_zone.hosted_zone.name_servers
}