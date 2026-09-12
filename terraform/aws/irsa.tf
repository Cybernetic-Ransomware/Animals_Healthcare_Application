# IAM roles assumable by in-cluster ServiceAccounts (IRSA), scoped to the
# OIDC provider Terraform creates via module.eks (enable_irsa = true).
#
# Each role's permissions come from a policy the iam module bundles and
# attaches as a customer-managed policy (attach_*_policy = true) — a JSON
# snapshot vendored inside the module, NOT the live AWS-managed policy of
# the same name. That snapshot only moves when the module version is
# bumped, so it can lag upstream; the EBS CSI supplement below covers one
# case where it does.
#
# Pinned to the iam module's 5.x line, not 6.x: iam/aws v6 requires AWS
# provider >= 6.28.0, which conflicts with the eks/vpc modules' own
# provider constraints (< 6.0.0) — mixing major lines across these
# community modules isn't possible in a single configuration. v5.x also
# keeps the -eks suffixed submodule name and the role_name input (renamed
# to name, with the module defaulting to prefix behavior, only in v6).

module "alb_controller_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "6.8.1" # exact pin — see the matching note on the eks module in eks.tf

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
  version = "6.8.1" # exact pin — see the matching note on the eks module in eks.tf

  role_name             = "${var.cluster_name}-ebs-csi"
  attach_ebs_csi_policy = true # module-bundled snapshot of AmazonEBSCSIDriverPolicy; supplemented below

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:ebs-csi-controller-sa"]
    }
  }
}

# The bundled EBS CSI policy (iam module 5.x) omits ec2:DescribeInstanceTypes,
# which the current aws-ebs-csi-driver calls to learn the per-instance-type
# volume attachment limit. Denied, the driver logs an UnauthorizedOperation
# and falls back to a hardcoded limit table — degraded, not broken, so this
# is a latent config defect rather than an outage (seen during the PR #28
# EKS rehearsal). Add just the one missing read action here instead of
# bumping the iam module to 6.x in this PR (6.x needs AWS provider >= 6.28,
# which the eks/vpc modules' constraints forbid — see the note above).
# ec2:DescribeInstanceTypes takes no resource-level scoping, hence "*".
resource "aws_iam_role_policy" "ebs_csi_describe_instance_types" {
  name = "${var.cluster_name}-ebs-csi-describe-instance-types"
  role = module.ebs_csi_irsa.iam_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "AllowDescribeInstanceTypes"
        Effect   = "Allow"
        Action   = "ec2:DescribeInstanceTypes"
        Resource = "*"
      }
    ]
  })
}
