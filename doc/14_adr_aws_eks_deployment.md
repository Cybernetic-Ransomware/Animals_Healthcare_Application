## AWS EKS deployment

### Date:
`2026-07-25`

### Status
Proposed

### Context
ADR-13 covers two GitOps targets — local minikube and the home k3s cluster — both assuming a
cluster already exists (minikube runs standalone; k3s is bootstrapped once on the home server
outside this repo). This adds a fourth, cloud-hosted target for demo/portfolio purposes. Unlike
the first two, the cluster itself does not pre-exist and must be provisioned as part of the
deploy story — the first Infrastructure-as-Code layer in this repository. It also needs a cloud
load balancer with real TLS and dynamic block storage, neither of which the home k3s/minikube
overlays had to solve (k3s ships Traefik and local-path storage out of the box).

### Decision
1. **EKS** (AWS-managed control plane) over self-managed k3s-on-EC2 — offloads control-plane
   operations for a target that is not meant to run continuously; the managed control plane is the
   part of a from-scratch cluster least worth hand-rolling for a demo.
2. **Terraform** (`terraform/aws/`) using the community modules `terraform-aws-modules/vpc/aws`
   and `terraform-aws-modules/eks/aws`, not hand-rolled resources. Correct subnet tagging for the
   ALB Controller's auto-discovery and OIDC provider wiring are exactly the boilerplate these
   modules exist to get right; re-deriving that from scratch would not teach anything the module
   source doesn't already show. **Local Terraform state**, git-ignored, is deliberate: a single
   operator and an ephemeral cluster (spun up per demo, torn down after) don't benefit from an S3
   backend, which would add its own bootstrap problem (something has to create the state bucket
   before Terraform can use it) for no gain at this scale.
3. **Terraform's scope is AWS-API-only**: VPC, EKS control plane, a managed node group (EC2, not
   Fargate — Fargate cannot back a StatefulSet with an EBS volume, and both Postgres and CouchDB
   are StatefulSets), IRSA IAM roles/policies, and the EKS-native addons (`vpc-cni`, `coredns`,
   `kube-proxy`, `aws-ebs-csi-driver`, the last via its own IRSA role). No `kubernetes`/`helm`
   Terraform providers anywhere: configuring one needs the cluster's endpoint, which does not
   exist until `module.eks` has already applied — the classic "provider depends on a resource from
   the same apply" problem. This also keeps a clean boundary already implicit in ADR-13: Terraform
   owns AWS account resources, kustomize/ArgoCD own cluster-internal state.
4. **AWS Load Balancer Controller installed manually via Helm**, not Terraform-managed — the one
   deliberate asymmetry against decision 3 (EBS CSI is an EKS addon; ALB Controller has no addon
   equivalent). Consistent with ADR-13 already treating ArgoCD's own install as a manual,
   version-pinned `kubectl apply --server-side` step rather than something IaC manages.
5. **ALB + ACM** for ingress/TLS (`ingressClassName: alb`, `alb.ingress.kubernetes.io/*`
   annotations) over ingress-nginx + cert-manager. Native AWS integration, ACM handles certificate
   renewal automatically, and it avoids running an extra ingress controller plus cert-manager pair
   on a small demo node group. IAM policies are attached via the module's
   `attach_load_balancer_controller_policy` / `attach_ebs_csi_policy` flags rather than vendoring
   AWS's published JSON policy documents — the module tracks upstream policy changes across its
   own releases.
6. **`gp3` StorageClass** shipped as a plain kustomize resource inside `overlays/aws` (wave `-3`,
   `is-default-class: "true"`), not a per-PVC `storageClassName` patch and not Terraform-managed.
   No PVC or `volumeClaimTemplate` in `kubernetes/base` sets `storageClassName` — this keeps base
   fully cluster-agnostic, exactly like the existing overlays that rely on their own cluster's
   default class.
7. **Sealed Secrets reused** for this fourth cluster (not External Secrets Operator) — the same
   4-secret set (`ahc-app-secrets`, `postgres-credentials`, `couchdb-credentials`,
   `flower-secrets`) and the same `kubeseal` workflow already documented for minikube/home.
   Consistency with a pattern the project is already invested in outweighs ESO's AWS-native
   advantages for a single additional cluster.
8. **`prepare-storage` initContainer left unpatched** in the `web`/`celery` Deployments. It exists
   (per ADR-13) because hostPath-backed provisioners (minikube, k3s local-path) ignore `fsGroup`.
   The EBS CSI driver *does* honor `fsGroup` with `fsGroupChangePolicy: OnRootMismatch` (already
   set), so on EKS `chown -R 1000:1000` runs against an already-correctly-owned volume — a fast,
   harmless no-op. Removing it would need a JSON-patch deleting an initContainer array element from
   a shared base Deployment, which is more overlay complexity than the no-op it would avoid, and it
   would make the pod spec structurally diverge between overlays.
9. **`argocd/ahc-aws.yaml` starts manual-sync-only** (no `automated:` block), mirroring the
   precedent `ahc-minikube-test` set for `ahc-home`: a new, unrehearsed cluster type gets observed
   step by step before any automation, promoted only after a drift/prune/secret-recovery pass.
10. **Not wired into CI's `bump`/`publish` flow.** `django.yml`'s `bump` job stays scoped to
    `overlays/home` only. Automating deploys to a cluster that is intermittently created and
    destroyed is actively wasteful and risky — a bump commit landing while the cluster doesn't
    exist just means a future `terraform apply` and first sync silently pick up whatever tag
    happens to be pinned. The image tag for `overlays/aws` is bumped manually
    (`kustomize edit set image`) before each demo, the same way `overlays/minikube-argocd` is
    pinned manually via `gh workflow run ... --ref <branch>` today. For the same reason, the CI
    `manifests` job does not render `overlays/aws` yet — it already skips `overlays/home` today
    for the identical reason (`sealed/` doesn't exist until a real cluster has sealed it); adding
    the aws render is a follow-up once its `sealed/` exists.
11. **No backup CronJobs on this overlay.** `overlays/home`'s `pg-backup`/`couchdb-export`/
    `files-backup` protect a long-running cluster; this cluster is explicitly spin-up/tear-down —
    `terraform destroy` removes any backup PVC along with everything else, so a same-cluster backup
    provides no real protection here.
12. **Cost-conscious defaults**: single managed node group pinned to one AZ (control-plane ENIs
    still span two AZs — an EKS requirement), one NAT gateway (not one per AZ), 2× `t3.medium`
    on-demand (not Spot — StatefulSets plus a short-lived demo aren't worth interruption/draining
    complexity). Not production sizing; a starting point for a bump if pods fail to schedule.

Rejected alternatives: Fargate (cannot back a StatefulSet with an EBS-backed PVC — no CSI node
DaemonSet support); self-managed k3s-on-EC2 (EKS chosen for its managed control plane); External
Secrets Operator + Secrets Manager (Sealed Secrets kept for consistency, decision 7);
ingress-nginx + cert-manager (ALB + ACM chosen, decision 5); Terraform-managed Helm release for the
ALB Controller (kept manual, decision 4); S3 remote state (local state, deliberate, decision 2).

### Consequences
- **Real, ongoing AWS cost while the cluster exists** — the only target in this project with a
  recurring bill. Rough all-in estimate if left running continuously: ~$73/mo EKS control plane +
  ~$60/mo (2× `t3.medium` on-demand) + ~$33/mo single NAT gateway + ~$16/mo ALB base + LCU charges
  + small EBS/data-transfer costs — roughly $180–200/month. `kubernetes/README-aws.md`'s teardown
  section is required reading, not optional, and setting an AWS Budget/billing alarm manually
  before the first `apply` is strongly recommended since Terraform cannot guarantee anyone
  remembers to destroy the cluster on schedule.
- **Teardown discipline is mandatory**: the ALB and EBS volumes are AWS resources created by
  controllers running *inside* the cluster, invisible to Terraform state. Destroying the VPC/EKS
  cluster out from under them orphans both — they keep billing with nothing left able to delete
  them through the normal path. The runbook requires deleting the Ingress/PVCs (or letting ArgoCD
  prune) *before* `terraform destroy`, plus a post-destroy check via `aws elbv2`/`aws ec2` for
  orphans.
- ACM + Route53 need a real, owned domain for DNS validation. Ships with `manage_dns = false` and
  a placeholder host (`ahc.example-aws-placeholder.com`) by default — `dns.tf`'s resources stay
  inert until both a domain and `manage_dns = true` are supplied.
- No backups means data loss on teardown is expected and accepted for this target — it is a
  demo/rehearsal environment, not a second production system.
- CI never deploys here automatically; every rollout is a deliberate manual act — slower than
  `overlays/home`'s auto-sync, which is the point.

### Keywords
- EKS,
- Terraform,
- IRSA,
- AWS Load Balancer Controller,
- ACM,
- EBS CSI,
- gp3,
- Sealed Secrets,
- cost-conscious IaC.

### Links
- [ADR-13](13_adr_gitops_argocd.md) — GitOps/ArgoCD baseline this extends.
- [kubernetes/README-aws.md](../kubernetes/README-aws.md) — bootstrap and teardown runbook.
- [terraform-aws-modules/eks/aws](https://github.com/terraform-aws-modules/terraform-aws-eks).
- [terraform-aws-modules/vpc/aws](https://github.com/terraform-aws-modules/terraform-aws-vpc).
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/).
- [Amazon EBS CSI driver](https://github.com/kubernetes-sigs/aws-ebs-csi-driver).
