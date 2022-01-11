# needed for ELB option
#variable "ingress_ips" {
#  type        = list
#  description = "List of Ingress IPs for security group"
#}
#variable "vpc_id" {
#  type        = string
#  description = "VPC id"
#}

variable "domain" {
  type = string
  description = "Cluster domain to create Route53 hosted zone"
}

variable "environment" {
  type        = string
  description = "Env"
}