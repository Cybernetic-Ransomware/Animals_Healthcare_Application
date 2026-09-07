## AWS EKS deployment

### Date:
`2026-07-25`

### Status
Done — design implemented and rehearsed end to end on a real EKS cluster in `eu-central-1`
on 2026-09-06/07 (commit `30c8948`), including a clean `terraform destroy`. Manual sync is a
kept, deliberate safety property, not a pre-automation phase (decision 9).

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
   `attach_load_balancer_controller_policy` / `attach_ebs_csi_policy` flags rather than
   hand-writing role policies. Note (rehearsal finding): those flags attach a JSON **snapshot the
   iam module bundles**, not the live AWS-managed policy, and the snapshot can lag upstream — the
   EBS CSI role needed a one-action supplement for `ec2:DescribeInstanceTypes` (see Consequences
   and `terraform/aws/irsa.tf`).
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
9. **`argocd/ahc-aws.yaml` is manual-sync-only** (no `automated:` block). This began as the
   same "observe a new cluster type before automating" bar `ahc-minikube-test` set for
   `ahc-home`; after the 2026-09-06/07 rehearsal it is **kept manual on purpose**, not promoted.
   The EKS target is ephemeral and cost-bearing — created per demo with `terraform apply`,
   destroyed straight after, absent in between. Auto-syncing a cluster that usually does not
   exist buys nothing and adds a path for a routine `main` push to read as an AWS deploy. Every
   AWS rollout stays two deliberate operator acts: a local `terraform apply`, then a manual sync.
10. **Not wired into CI's `bump`/`publish` deploy flow.** `django.yml`'s `bump` job stays scoped
    to `overlays/home` only, and no job runs `terraform apply`/`destroy` or syncs `ahc-aws` —
    automating deploys to an intermittently-existing cluster is wasteful and risky. The
    `overlays/aws` image tag is bumped by hand (`kustomize edit set image`) before each demo,
    like `overlays/minikube-argocd`. CI **does** now render and statically validate
    `overlays/aws` in the `manifests` job (its `sealed/` files exist as of PR #28): assertions
    cover the rehearsal invariants (SealedSecret waves, PVC waves, co-location affinity, no node
    pinning) plus a guardrail that fails if `ahc-aws` gains `automated:`, if the workflow gains a
    `terraform apply`/`destroy`, or if `bump` starts touching `overlays/aws`. Render/validate
    only — never deploy.
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
- **The design was rehearsed end to end on a real EKS cluster (2026-09-06/07, `eu-central-1`,
  commit `30c8948`)** and torn down cleanly (`terraform destroy` — 65 resources; no orphaned
  ALB / EBS / NAT / EIP). Three EKS-only behaviours surfaced and are now folded into the
  `overlays/aws` design (details in `kubernetes/README-aws.md`):
  - *gp3 `WaitForFirstConsumer` vs sync-wave* — the base app PVCs at wave `-3` deadlock ArgoCD
    on EKS (nothing binds them until a consumer schedules at wave `0`); the overlay patches
    both PVCs to wave `0`.
  - *ReadWriteOnce co-location* — `app-private-pvc` is RWO and mounted by both `ahc-app-backend`
    and `celery-worker`; the overlay co-locates them with a `colocation-group` label +
    `requiredDuringSchedulingIgnoredDuringExecution` pod affinity on
    `topologyKey: kubernetes.io/hostname`, no hardcoded node name.
  - *EBS CSI IAM gap* — the iam module's bundled EBS CSI policy snapshot lacks
    `ec2:DescribeInstanceTypes`; `irsa.tf` adds a one-action inline supplement.
- TLS/HTTPS against a real ACM certificate + owned domain was **not** exercised (the rehearsal
  ran HTTP-only, domainless, with live-only `ALLOWED_HOSTS="*"`); that path remains untested.

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
