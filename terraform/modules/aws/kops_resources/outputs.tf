output "kops_s3_bucket_name" {
  value = aws_s3_bucket.kops_state.bucket
}

output "kops_hosted_zone_name_servers" {
  value = aws_route53_zone.hosted_zone.name_servers
}