provider "aws" {
  region = "ap-northeast-1"
  shared_credentials_file = "~/.aws/credentials"
  profile = "default"
}

module "glue" {
  source = "./modules/aws/glue"
}