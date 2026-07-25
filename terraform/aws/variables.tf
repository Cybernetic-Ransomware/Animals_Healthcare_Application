variable "aws_region" {
  type        = string
  description = "AWS region for the cluster and its VPC."
  default     = "eu-central-1"
}

variable "cluster_name" {
  type        = string
  description = "EKS cluster name, also used as a prefix for related resource names."
  default     = "ahc-eks-demo"
}

variable "cluster_version" {
  type        = string
  description = "Kubernetes version for the EKS control plane."
  default     = "1.30"
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for the cluster VPC."
  default     = "10.60.0.0/16"
}

variable "node_instance_types" {
  type        = list(string)
  description = "EC2 instance types for the managed node group."
  default     = ["t3.medium"]
}

variable "node_desired_size" {
  type        = number
  description = "Desired node count in the managed node group."
  default     = 2
}

variable "node_min_size" {
  type        = number
  description = "Minimum node count in the managed node group."
  default     = 1
}

variable "node_max_size" {
  type        = number
  description = "Maximum node count in the managed node group."
  default     = 3
}

variable "manage_dns" {
  type        = bool
  description = "Whether to create Route53/ACM resources in dns.tf. Requires a real, owned domain — leave false until one exists."
  default     = false
}

variable "domain_name" {
  type        = string
  description = "Route53 hosted zone domain (e.g. example.com). Only used when manage_dns = true."
  default     = ""
}
