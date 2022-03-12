output "ecr_repo_name" {
  value = aws_ecr_repository.ecr_repo.name
}

output "ecr_repo_registry_id" {
  value = aws_ecr_repository.ecr_repo.registry_id
}

output "ecr_repo_url" {
  value = aws_ecr_repository.ecr_repo.repository_url
}