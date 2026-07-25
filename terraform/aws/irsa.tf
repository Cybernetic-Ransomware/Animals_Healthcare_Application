# IAM roles assumable by in-cluster ServiceAccounts (IRSA), scoped to the
# OIDC provider Terraform creates via module.eks (enable_irsa = true).
# Both roles attach an AWS-managed/published policy through the module
# rather than a vendored JSON copy — the module tracks upstream policy
# changes across its own releases.
#
# Pinned to the iam module's 5.x line, not 6.x: iam/aws v6 requires AWS
# provider >= 6.28.0, which conflicts with the eks/vpc modules' own
# provider constraints (< 6.0.0) — mixing major lines across these
# community modules isn't possible in a single configuration. v5.x also
# keeps the -eks suffixed submodule name and the role_name input (renamed
# to name, with the module defaulting to prefix behavior, only in v6).

module "alb_controller_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  role_name                              = "${var.cluster_name}-alb-controller"
  attach_load_balancer_controller_policy = true

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:aws-load-balancer-controller"]
    }
  }
}

module "ebs_csi_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  role_name             = "${var.cluster_name}-ebs-csi"
  attach_ebs_csi_policy = true # AWS managed policy: AmazonEBSCSIDriverPolicy

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:ebs-csi-controller-sa"]
    }
  }
}
