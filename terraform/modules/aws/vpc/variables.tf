variable "name" {
  type        = string
  description = "VPC name"
}

variable "environment" {
  type        = string
  description = "Name prefix"
}

variable "cidr" {
  type        = string
  description = "vpc cidr"
}

variable "azs" {
  type        = list
  description = "Availability zones list"
}

variable "private_subnets" {
  type        = list
  description = "List of private subnets in the vpc"
}

variable "public_subnets" {
  type        = list
  description = "Public subnets list"
}

variable "cluster_name" {
  type        = string
  description = "FQDN cluster name"
}

variable "enable_nat_gateway" {
  type        = bool
  description = "Enable nat gateway"
}

variable "single_nat_gateway" {
  type        = bool
  description = "Single nat gateway"
}

variable "one_nat_gateway_per_az" {
  type        = bool
  description = "One nat gateway per az"
}