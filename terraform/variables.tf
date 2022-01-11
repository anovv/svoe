variable "region" {
  type        = string
  description = "AWS region"
}

variable "vpc_name" {
  type        = string
  description = "VPC name"
}

variable "environment" {
  type        = string
  description = "Env"
}

variable "cidr" {
  type        = string
  description = "vpc cidr"
}

variable "azs" {
  type        = list(any)
  description = "Availability zones list"
}

variable "private_subnets" {
  type        = list(any)
  description = "List of private subnets in the vpc"
}

variable "public_subnets" {
  type        = list(any)
  description = "Public subnets list"
}

#variable "ingress_ips" {
#  type        = list(any)
#  description = "List of Ingress IPs for security group"
#}

variable "k8s_non_masquerade_cidr" {
  type        = string
  description = "nonMasqueradeCIDR for cluster"
}

variable "cluster_name_prefix" {
  type        = string
  description = "Name prefix. Full name is {prefix}.{environment}.{domain}"
}

variable "domain" {
  type        = string
  description = "Domain to host cluster"
}
