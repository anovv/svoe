provider "aws" {
  region                  = "ap-northeast-1"
  shared_credentials_file = "~/.aws/credentials"
  profile                 = "default"
}

resource "aws_s3_bucket" "kops_state" {
  bucket = var.kops_s3_bucket_name
  acl    = "private"

  versioning {
    enabled = true
  }

  tags = {
    Application = "kops"
    Description = "S3 Bucket for KOPS state"
  }
}

resource "aws_route53_zone" "hosted_zone" {
  name = var.domain
}