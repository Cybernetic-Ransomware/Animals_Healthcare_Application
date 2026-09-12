module "eks" {
  source = "terraform-aws-modules/eks/aws"
  # Exact pin (lockfile only pins providers, not modules); 21.x needs AWS provider >= 6.28, incompatible with our ~> 5.0.
  version = "21.25.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets # control plane ENIs span both AZs

  enable_irsa = true # required for the ALB controller and EBS CSI IAM roles in irsa.tf

  cluster_endpoint_public_access = true # kubectl from a laptop; no bastion for a demo cluster

  # The module defaults this to false and defines no access_entries, which
  # leaves the cluster creator with zero API access after `apply` —
  # `kubectl get nodes` would fail with Unauthorized. Simplicity is
  # appropriate for a single-operator demo cluster; a longer-lived,
  # multi-operator cluster should use explicit access_entries instead.
  enable_cluster_creator_admin_permissions = true

  eks_managed_node_groups = {
    default = {
      # Pinned to one AZ/subnet: StatefulSets (postgres, couchdb) and the
      # web/celery pods talking to them stay same-AZ, avoiding cross-AZ
      # data transfer charges on top of the NAT/ALB cost already present.
      # Fargate is not an option here — it cannot back a StatefulSet with
      # an EBS-backed PVC (no CSI node DaemonSet support), so both database
      # StatefulSets require an EC2-backed managed node group regardless.
      subnet_ids     = [module.vpc.private_subnets[0]]
      instance_types = var.node_instance_types
      min_size       = var.node_min_size
      max_size       = var.node_max_size
      desired_size   = var.node_desired_size
      capacity_type  = "ON_DEMAND" # not Spot: StatefulSets + a short-lived demo aren't worth interruption/draining complexity
    }
  }

  # vpc-cni/coredns/kube-proxy are the baseline EKS addons. aws-ebs-csi-driver
  # is required for dynamic PVC provisioning (not preinstalled on EKS) — its
  # IRSA role is defined in irsa.tf. The AWS Load Balancer Controller has no
  # EKS-addon equivalent and is installed manually via Helm (see
  # kubernetes/README-aws.md) — see ADR-14 for why that asymmetry is deliberate.
  cluster_addons = {
    vpc-cni    = {}
    coredns    = {}
    kube-proxy = {}
    aws-ebs-csi-driver = {
      service_account_role_arn = module.ebs_csi_irsa.iam_role_arn
    }
  }
}
