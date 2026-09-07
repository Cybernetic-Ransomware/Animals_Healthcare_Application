terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Local state, deliberately: single operator, ephemeral demo cluster
  # (spun up for a demo, torn down afterwards). An S3 backend would add its
  # own bootstrap problem (something has to create the bucket before
  # Terraform can use it) for no benefit at this scale. Revisit only if
  # this cluster becomes long-lived or multi-operator — see ADR-14.
}
