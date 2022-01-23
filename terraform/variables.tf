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
