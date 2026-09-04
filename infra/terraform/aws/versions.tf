terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  backend "s3" {
    # bucket = "bi-platform-tfstate-PROD"  # set via -backend-config
    # key    = "aws/prod.tfstate"
    # region = "us-east-1"
  }
}

provider "aws" {
  region = var.region
  default_tags { tags = var.tags }
}
