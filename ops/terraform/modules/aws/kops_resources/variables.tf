variable "domain" {
  type = string
  description = "Cluster domain to create Route53 hosted zone"
}

variable "kops_s3_bucket_name" {
  type        = string
  description = "Bucket name for cluster states"
}