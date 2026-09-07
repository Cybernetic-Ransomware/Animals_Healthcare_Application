provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "animals-healthcare-application"
      ManagedBy = "terraform"
      Cluster   = var.cluster_name
    }
  }
}
