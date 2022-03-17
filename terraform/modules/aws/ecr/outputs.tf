output "svoe_data_feed_ecr_repo_name" {
  value = aws_ecr_repository.svoe_data_feed_ecr_repo.name
}

output "svoe_data_feed_ecr_repo_registry_id" {
  value = aws_ecr_repository.svoe_data_feed_ecr_repo.registry_id
}

output "svoe_data_feed_ecr_repo_url" {
  value = aws_ecr_repository.svoe_data_feed_ecr_repo.repository_url
}