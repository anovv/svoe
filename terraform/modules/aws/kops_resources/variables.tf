variable "ingress_ips" {
  type        = list
  description = "List of Ingress IPs for security group"
}

variable "environment" {
  type        = string
  description = "Env"
}

variable "vpc_id" {
  type        = string
  description = "VPC id"
}