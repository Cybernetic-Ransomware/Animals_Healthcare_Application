# IAM roles assumable by in-cluster ServiceAccounts (IRSA), scoped to the
# OIDC provider Terraform creates via module.eks (enable_irsa = true).
# Both roles attach an AWS-managed/published policy through the module
# rather than a vendored JSON copy — the module tracks upstream policy
# changes across its own releases.
#
# The submodule lived at terraform-aws-modules/eks/aws//modules/
# iam-role-for-service-accounts-eks through v19; it was removed in the
# eks module's v20.0.0 and now lives in the separate iam module as
# iam-role-for-service-accounts (no "-eks" suffix). Its role_name input
# was also renamed to name.

module "alb_controller_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts"
  version = "~> 6.0"

  name            = "${var.cluster_name}-alb-controller"
  use_name_prefix = false # a stable, predictable role name is worth more here than the module's default random suffix

  attach_load_balancer_controller_policy = true

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:aws-load-balancer-controller"]
    }
  }
}

module "ebs_csi_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts"
  version = "~> 6.0"

  name            = "${var.cluster_name}-ebs-csi"
  use_name_prefix = false

  attach_ebs_csi_policy = true # AWS managed policy: AmazonEBSCSIDriverPolicy

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:ebs-csi-controller-sa"]
    }
  }
}
