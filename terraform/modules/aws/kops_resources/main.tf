resource "aws_s3_bucket" "kops_state" {
  bucket = "${var.environment}-kops-s3"
  acl    = "private"

  versioning {
    enabled = true
  }

  tags = {
    Environment = var.environment
    Application = "kops"
    Description = "S3 Bucket for KOPS state"
  }
}

resource "aws_security_group" "k8s_security_group" {
  name   = "${var.environment}-k8s-sg"
  vpc_id = var.vpc_id
  tags = {
    environment = var.environment
    terraform   = true
  }

  ingress {
    protocol    = "tcp"
    from_port   = 80
    to_port     = 80
    cidr_blocks = var.ingress_ips
  }

  ingress {
    protocol    = "tcp"
    from_port   = 443
    to_port     = 443
    cidr_blocks = var.ingress_ips
  }
}