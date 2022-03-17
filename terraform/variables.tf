variable "multicluster_config" {
  type = list(map(string))
  description = "List of cluster configurations"
}

variable "kops_s3_bucket_name" {
  type = string
  description = "S3 bucket for clusters state"
}

variable "domain" {
  type        = string
  description = "Domain to host clusters"
}

variable "svoe_data_feed_ecr_repo_name" {
  type        = string
  description = "Repository name in ECR for Svoe Data Feed service"
}
