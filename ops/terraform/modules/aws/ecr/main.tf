provider "aws" {
  region                  = "ap-northeast-1" # TODO parametrize default region?
  shared_credentials_file = "~/.aws/credentials"
  profile                 = "default"
}

resource "aws_ecr_repository" "svoe_data_feed_ecr_repo" {
  name                 = var.svoe_data_feed_ecr_repo_name
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
}

# TODO add aws_ecr_repository_policy