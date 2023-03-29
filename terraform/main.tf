provider "aws" {
  region = var.aws_region
}

terraform {
  required_version = "~> 1.4.0"
}

# module "lambda" {
#   source = "./modules/lambda"
# }
