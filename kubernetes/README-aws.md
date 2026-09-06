# AWS EKS deployment — ops runbook

See [ADR-14](../doc/14_adr_aws_eks_deployment.md) for the decisions behind this target and
[`kubernetes/README.md`](README.md) for the other (free) deployment targets.

⚠️ **Unlike every other target in this repo, this one costs real money while running.** Read
"Cost" and "Teardown" before running `terraform apply`.

## Layout

| Path | Purpose |
|---|---|
| `terraform/aws/` | Provisions the EKS cluster itself: VPC, control plane, managed node group, IRSA roles, EKS addons |
| `kubernetes/overlays/aws/` | Kustomize overlay: ALB ingress, gp3 StorageClass, SealedSecrets for this cluster |
| `argocd/ahc-aws.yaml` | ArgoCD Application, manual sync only (new cluster type, unrehearsed) |

Terraform's scope is AWS-API-only (VPC, EKS, node group, IRSA, EKS-native addons). It does **not**
install the AWS Load Balancer Controller or ArgoCD — both are manual, version-pinned steps below,
for the same reason ArgoCD's own install is manual in the other runbook (see ADR-14, decision 4).

## Cost

Rough estimate if left running continuously: ~$73/mo EKS control plane + ~$60/mo (2×
`t3.medium` on-demand) + ~$33/mo single NAT gateway + ~$16/mo ALB base + LCU charges + small
EBS/data-transfer costs — **roughly $180–200/month**. Set an AWS Budget/billing alarm manually in
the console before your first `apply`; Terraform cannot guarantee anyone remembers to destroy the
cluster on schedule.

## Prerequisites

- AWS account and credentials configured locally (`aws configure` or an SSO profile).
- Terraform >= 1.7, `kubectl`, `helm`, `kubeseal` (see `kubernetes/README.md`'s "Sealing secrets"
  section for how to get `kubeseal` on Windows).
- Optional: a real, owned domain if you want a working ALB certificate via ACM/Route53. Without
  one, leave `manage_dns = false` (the default) — the overlay ships with a placeholder host that
  will never get a valid ALB, which is a safe, documented resting state.

## Bootstrap (first time)

```powershell
# 1. Provision AWS infrastructure
cd terraform/aws
Copy-Item terraform.tfvars.example terraform.tfvars   # edit region/cluster_name/domain as needed
terraform init
terraform plan -out=tfplan
terraform apply tfplan

# 2. Point kubectl at the new cluster
terraform output -raw configure_kubectl | Invoke-Expression
kubectl get nodes

# 3. Install the AWS Load Balancer Controller (manual Helm — see ADR-14 decision 4 for why)
$AlbRoleArn = terraform output -raw alb_controller_role_arn
$ClusterName = terraform output -raw cluster_name
$Region = terraform output -raw region
$VpcId = terraform output -raw vpc_id
helm repo add eks https://aws.github.io/eks-charts
helm repo update
helm install aws-load-balancer-controller eks/aws-load-balancer-controller `
  -n kube-system `
  --set clusterName=$ClusterName `
  --set serviceAccount.create=true `
  --set serviceAccount.name=aws-load-balancer-controller `
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=$AlbRoleArn `
  --set region=$Region `
  --set vpcId=$VpcId
kubectl -n kube-system rollout status deploy/aws-load-balancer-controller

# 4. Verify the EBS CSI driver is healthy (installed as a Terraform-managed EKS addon)
kubectl -n kube-system get pods -l app=ebs-csi-controller
# gp3 becomes default once the aws overlay's first sync applies storageclass-gp3.yaml (step 8);
# until then this shows only whatever EKS shipped by default (commonly gp2).
kubectl get storageclass

# 5. Install ArgoCD — same pinned version/flags as the minikube/home rehearsal
#    (deliberately NO Ingress for ArgoCD itself: reach the UI via port-forward,
#    sidestepping the ALB Controller/ArgoCD chicken-and-egg entirely)
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
$ArgoCdVersion = "v3.4.5"   # keep in sync with kubernetes/README.md's pinned version
kubectl apply -n argocd --server-side --force-conflicts -f "https://raw.githubusercontent.com/argoproj/argo-cd/$ArgoCdVersion/manifests/install.yaml"
kubectl -n argocd port-forward svc/argocd-server 8080:443   # separate terminal

# 6. Bootstrap sealed-secrets, then seal the 4 secrets for THIS cluster
kubectl apply -f argocd/sealed-secrets.yaml
kubectl -n kube-system rollout status deploy/sealed-secrets-controller

# 6a. Fetch the controller's PUBLIC sealing certificate.
#     `kubeseal --controller-namespace kube-system --fetch-cert` needs a
#     network route from your workstation to the controller Service; on an
#     EKS cluster where that isn't reachable, kubeseal (0.39.1 observed)
#     falls back to dialing the controller pod IP directly (e.g.
#     10.60.x.x:8080) and times out. Read the same public cert straight
#     from the active sealing-key Secret through the Kubernetes API instead
#     — this pulls only `tls.crt`, the public half of the key pair; the
#     private key never leaves the cluster:
$CertB64 = kubectl -n kube-system get secret `
  -l sealedsecrets.bitnami.com/sealed-secrets-key=active `
  -o jsonpath='{.items[0].data.tls\.crt}'
[IO.File]::WriteAllBytes(
  (Join-Path (Get-Location) "aws.pem"),
  [Convert]::FromBase64String($CertB64)
)
Get-Content .\aws.pem -TotalCount 2   # sanity check: -----BEGIN CERTIFICATE-----

# 6b. Seal each secret against that cert. aws.pem holds only the public
#     certificate, but it is git-ignored (*.pem) and stays out of the repo.
Get-Content kubernetes/overlays/minikube-local/secrets/app-secret.yaml |
  kubeseal --cert aws.pem --format yaml |
  Set-Content kubernetes/overlays/aws/sealed/app-sealedsecret.yaml
# repeat for postgres-secret, couchdb-secret, flower-secret
```

## Sealing secrets for aws

Same 4-secret set and workflow as `kubernetes/README.md`'s "Sealing secrets" section
(`ahc-app-secrets`, `postgres-credentials`, `couchdb-credentials`, `flower-secrets`), sealed
against this cluster's controller key into `kubernetes/overlays/aws/sealed/`. `SealedSecret`s are
bound to the private key of the controller that encrypted them — a file sealed for minikube or
home will not decrypt on this cluster, even with an identical name and namespace.

```powershell
# 7. Fill in the real domain + ACM certificate ARN (or leave the placeholder
#    and accept the ALB will fail to provision a listener until a real
#    certificate exists — see kubernetes/overlays/aws/ingress-patch.yaml)
#    edit kubernetes/overlays/aws/{ingress-patch.yaml,configmap-patch.yaml}

git add kubernetes/overlays/aws/sealed kubernetes/overlays/aws/ingress-patch.yaml kubernetes/overlays/aws/configmap-patch.yaml
git commit -m "feat(k8s): seal aws overlay secrets and set real domain"
git push
```

## First sync

```powershell
# 8. Apply the Application and trigger a manual sync (no argocd CLI needed,
#    same technique as the minikube rehearsal)
kubectl apply -f argocd/ahc-aws.yaml
kubectl -n argocd patch application ahc-aws --type merge -p '{"operation":{"initiatedBy":{"username":"manual"},"sync":{"revision":"main","syncStrategy":{"hook":{}}}}}'

# A sync stuck on resources that can never become healthy will not stop when
# the operation field is removed. Preferred: `argocd app terminate-op ahc-aws`.
# Emergency workaround if the argocd CLI isn't available (reaches into
# controller-internal state — see kubernetes/README.md's troubleshooting note):
# kubectl -n argocd patch application ahc-aws --type merge -p '{"status":{"operationState":{"phase":"Terminating"}}}'

# 9. Smoke test
kubectl -n ahc get ingress ingress-service      # note the ALB hostname once provisioned
curl.exe -f https://<alb-hostname-or-domain>/livez
curl.exe -f https://<alb-hostname-or-domain>/readyz
```

## Manual image bump

Not wired into CI (see ADR-14, decision 10) — bump the tag by hand before each demo:

```powershell
cd kubernetes/overlays/aws
kustomize edit set image "ghcr.io/<owner>/ahc-app=ghcr.io/<owner>/ahc-app:sha-<commit>"
git add kustomization.yaml
git commit -m "chore(deploy): bump aws overlay to sha-<commit>"
git push
# then repeat the manual sync command from "First sync" step 8
```

## Teardown

**Read this before running `terraform destroy`.** Terraform has no idea an `Ingress` provisioned
an ALB, or that a `PersistentVolumeClaim` provisioned an EBS volume — those are AWS resources
created by controllers running *inside* the cluster, outside Terraform's state. Destroying the
VPC/EKS cluster out from under them orphans the ALB and EBS volumes: they keep billing
indefinitely with nothing left able to delete them through the normal path.

**If you ran a domainless rehearsal, first revert every live-only change** (HTTP-only Ingress,
`ALLOWED_HOSTS="*"`, any temporary `nodeSelector`) — see "Running the rehearsal without a
domain" below. They are live-cluster edits that never went into Git, so nothing else removes
them, and an HTTP-only Ingress rebuilt from stale state leaves a misleading `OutOfSync`
Application.

```powershell
# 1. Let ArgoCD/kubectl clean up cluster-created AWS resources FIRST, while
#    the ALB Controller and EBS CSI driver are still alive to process the
#    deletions (this is the step that actually removes the ALB and EBS
#    volumes, via their controllers' finalizers)
kubectl delete -f argocd/ahc-aws.yaml
kubectl -n ahc delete ingress ingress-service --ignore-not-found
kubectl -n ahc delete pvc --all
kubectl -n ahc get ingress,pvc                  # confirm empty before proceeding

# 2. THEN tear down the infrastructure
cd terraform/aws
terraform destroy

# 3. Verify no orphans (belt-and-suspenders — check even after step 1)
aws elbv2 describe-load-balancers --region <region> | findstr <cluster-name>
aws ec2 describe-volumes --region <region> --filters "Name=status,Values=available"
```

If step 1 is skipped, or the cluster is already gone before it runs, the ALB and EBS volumes must
be deleted manually via the AWS console/CLI — they will not disappear on their own and will
continue billing.

## AWS overlay specifics & rehearsal learnings

Everything below is EKS-specific and was found (or confirmed) during the PR #28 rehearsal on a
real cluster. The base manifests are unchanged; the AWS behaviour lives in
`kubernetes/overlays/aws/` patches.

### Storage: gp3, `WaitForFirstConsumer`, and sync-wave ordering

- `storageclass-gp3.yaml` sets `volumeBindingMode: WaitForFirstConsumer`. An EBS volume is not
  provisioned or bound until a Pod that mounts the PVC is scheduled — the opposite of the
  hostPath provisioners the minikube/k3s overlays use, which bind immediately.
- Consequence: **an app PVC must not sit in an earlier ArgoCD sync-wave than the workload that
  consumes it.** The base puts `app-media-pvc` / `app-private-pvc` at wave `-3` (correct for
  hostPath). On EKS that deadlocks: ArgoCD blocks on wave `-3` until the PVCs are `Bound`, but
  nothing binds them until their consumers (`ahc-app-backend`, `celery-worker`, wave `0`) run.
- Fix: `pvc-sync-wave-patch.yaml` moves both PVCs to wave `0` **in this overlay only**, so they
  land alongside their consumers. Strategic-merge merges `metadata.annotations`, so the base's
  `argocd.argoproj.io/sync-options: Prune=false,Delete=false` carries through to the rendered
  PVC regardless; the patch also restates it so the file shows the full annotation set.

### Single-node co-location of web + worker

- `app-private-pvc` is `ReadWriteOnce`. gp3 EBS enforces that literally — the volume attaches to
  one node. `ahc-app-backend` and `celery-worker` both mount it, so if the scheduler places them
  on different nodes the second Pod fails with `Multi-Attach error for volume`.
- The rehearsal's throwaway fix was a hardcoded `nodeSelector` on a specific
  `kubernetes.io/hostname`. **That must never reach the repo** — the hostname is different on
  every cluster.
- Repo fix: `colocation-patch.yaml` gives both Pod templates the dedicated label
  `colocation-group: app-private-rwo` and both declare the **same**
  `requiredDuringSchedulingIgnoredDuringExecution` pod affinity selecting that label, keyed on
  `topologyKey: kubernetes.io/hostname`. Node-name agnostic, works on any cluster.
- Symmetric required self-affinity does not deadlock at cold start: the scheduler special-cases
  the first Pod of an affinity group — with no Pod yet matching the selector, the Pod matching
  its own selector, and a node satisfying the topologyKey, it places that first Pod anyway. The
  rest of the group then has a Pod to attract to and converges onto the same node.
- Single replica each in this demo architecture. If either workload is scaled past one replica,
  or moved off the shared RWO volume, revisit this patch.

### EBS CSI needs `ec2:DescribeInstanceTypes`

- `terraform/aws/irsa.tf` sets `attach_ebs_csi_policy = true`. In iam module 5.x that attaches a
  **module-bundled JSON snapshot** of `AmazonEBSCSIDriverPolicy`, not the live AWS-managed
  policy — and the snapshot lags: it lacks `ec2:DescribeInstanceTypes`, which the current driver
  calls to learn the per-instance-type volume attachment limit.
- Denied, the driver logs `UnauthorizedOperation` and falls back to a hardcoded limit table —
  degraded, not broken. `irsa.tf` adds a one-action inline role policy
  (`aws_iam_role_policy.ebs_csi_describe_instance_types`) rather than bumping the iam module to
  6.x (which would force AWS provider >= 6.28, incompatible with the eks/vpc modules here).

### Production still assumes a real domain + ACM certificate

The committed AWS manifests are the production shape: `ingress-patch.yaml` carries a
`certificate-arn` placeholder and HTTPS listener, `configmap-patch.yaml` carries a placeholder
`AHC_DOMAIN` in `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS`. With `manage_dns = false` and the
placeholders left in place, the ALB never gets a valid listener — a safe resting state, but not
a running app.

### Running the rehearsal without a domain

To exercise the full sync on a cluster with no owned domain, the rehearsal applied **live-only**
changes directly to the running cluster (`kubectl edit` / `patch`), never committed:

- **HTTP-only ALB** — on the live `ingress-service`: drop the
  `alb.ingress.kubernetes.io/certificate-arn` and `.../ssl-redirect` annotations and set
  `alb.ingress.kubernetes.io/listen-ports: '[{"HTTP":80}]'`. The ALB then provisions a plain
  port-80 listener and serves on its `*.elb.amazonaws.com` hostname.
- **`ALLOWED_HOSTS="*"`** — on the live `ahc-app-config` ConfigMap, so Django accepts requests
  with the ALB hostname as `Host` (which is not known ahead of time), then
  `kubectl -n ahc rollout restart deploy/ahc-app-backend`.

> **`ALLOWED_HOSTS="*"` is a rehearsal shortcut, not a production recommendation.** It disables
> Django's Host-header validation entirely. Production must list the real domain(s).

Because these live-only edits diverge from Git, ArgoCD shows the Application as `OutOfSync`.
That is expected during a rehearsal; do not "fix" it by committing the shortcuts.

### Validating the overlay locally

```powershell
# Render the overlay (needs kubernetes/overlays/aws/sealed/ to exist)
kubectl kustomize kubernetes/overlays/aws | Out-Null

# Spot-check the rehearsal invariants in the rendered output
kubectl kustomize kubernetes/overlays/aws |
  Select-String 'sync-wave|colocation-group|topologyKey|Multi-Attach' -Context 0,1

# Terraform (no cloud credentials, no state mutation)
terraform -chdir=terraform/aws fmt -check -recursive
terraform -chdir=terraform/aws validate   # after `terraform -chdir=terraform/aws init -backend=false`

git diff --check
```

CI (`.github/workflows/django.yml`, `manifests` job) renders this overlay and asserts the four
SealedSecrets at wave `-3`, both app PVCs at wave `0` with `Prune=false,Delete=false` intact, the
shared `colocation-group` label plus a matching `requiredDuringSchedulingIgnoredDuringExecution`
pod-affinity term keyed on `kubernetes.io/hostname` on both `ahc-app-backend` and `celery-worker`,
and that no workload pins a literal node name.

## Troubleshooting

See `kubernetes/README.md`'s "GitOps rehearsal" section for ArgoCD-level troubleshooting (stuck
syncs, `--server-side` apply, terminating an operation) — it applies identically here, this
overlay just points at a different cluster and Application name (`ahc-aws`).
