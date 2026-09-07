# EKS addons (vpc-cni, coredns, kube-proxy, aws-ebs-csi-driver) are declared
# via cluster_addons on module "eks" in eks.tf — a single module argument is
# enough, no standalone aws_eks_addon resources needed. This file exposes
# what the manual post-apply steps in kubernetes/README-aws.md need.

output "cluster_name" {
  value = module.eks.cluster_name
}

output "region" {
  value = var.aws_region
}

output "vpc_id" {
  value = module.vpc.vpc_id
}

output "alb_controller_role_arn" {
  value = module.alb_controller_irsa.iam_role_arn
}

output "acm_certificate_arn" {
  value = var.manage_dns ? aws_acm_certificate.this[0].arn : null
}

output "configure_kubectl" {
  value = "aws eks update-kubeconfig --name ${module.eks.cluster_name} --region ${var.aws_region}"
}
