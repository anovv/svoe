cluster_name    = "apn1.k8s.local" # should contain .local for Gossip DNS
environment     = "dev"
region          = "ap-northeast-1"
cidr            = "10.0.0.0/16"
azs             = ["ap-northeast-1a"]
private_subnets = []
public_subnets  = ["10.0.101.0/24"]
ingress_ips     = ["10.0.0.0/16"]
