# AWS EKS deployment — ops runbook

See [ADR-14](../doc/14_adr_aws_eks_deployment.md) for the decisions behind this target and
[`kubernetes/README.md`](README.md) for the other (free) deployment targets.

⚠️ **Unlike every other target in this repo, this one costs real money while running.** Read
"Cost" and "Teardown" before running `terraform apply`.

## AWS safety contract

AWS/EKS is a **cost-bearing, ephemeral** target: it is created for a demo and destroyed
immediately after (see "Teardown"). Nothing in this repo brings it up on its own — treat the
following as a contract, not a description of current wiring that might drift:

- **CI never touches AWS.** `.github/workflows/django.yml` runs no `terraform apply`, no
  `terraform destroy`, creates no EKS cluster, and never syncs the `ahc-aws` ArgoCD
  Application. No job configures AWS credentials.
- **What CI *does* do for this target:** renders and validates the `overlays/aws` kustomize
  overlay, runs `terraform -chdir=terraform/aws fmt -check` / `validate` / `init -backend=false`
  (no cloud, no state), and — on `push` to `main` or `workflow_dispatch` — publishes a
  `sha-<commit>` image to GHCR.
- **`workflow_dispatch` from a branch cannot move `prod`.** The `prod` tag is pushed only on
  `refs/heads/main`; a branch dispatch publishes `sha-<commit>` only.
- **An AWS deployment is two separate, deliberate operator actions:** (1) a local
  `terraform apply` in `terraform/aws/`, then (2) a manual ArgoCD sync of `ahc-aws`.
  Neither happens from a merge, a push, or CI.
- **`argocd/ahc-aws.yaml` is manual-sync-only by design** (no `spec.syncPolicy.automated`),
  and stays that way — see the comment in that file.
- **Merge/push to `main` runs the HOME CD path, never AWS.** CI's `bump` job rewrites the image
  tag in `kubernetes/overlays/home` only; the home k3s cluster's ArgoCD auto-syncs that. The
  `aws` overlay's image tag is only ever bumped by hand before a demo.

| | HOME CD (automatic) | AWS deployment (manual) |
|---|---|---|
| Trigger | push / merge to `main` | operator runs `terraform apply`, then a manual sync |
| Image tag bump | CI `bump` job, `overlays/home` | `kustomize edit set image` by hand, `overlays/aws` |
| ArgoCD sync | `ahc-home`, `automated: {prune, selfHeal}` | `ahc-aws`, manual only |
| Cluster lifetime | long-running home server | created per demo, destroyed after |
| Cost | electricity | ~$180–200/month while up |

## Layout

| Path | Purpose |
|---|---|
| `terraform/aws/` | Provisions the EKS cluster itself: VPC, control plane, managed node group, IRSA roles, EKS addons |
| `kubernetes/overlays/aws/` | Kustomize overlay: ALB ingress, gp3 StorageClass, SealedSecrets for this cluster |
| `argocd/ahc-aws.yaml` | ArgoCD Application, manual sync only (deliberate — ephemeral, cost-bearing target; see "AWS safety contract") |

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
#    sidestepping the ALB Controller/ArgoCD chicken-and-egg entirely).
#    v3.5.2 was rehearsed on minikube only (see kubernetes/README.md "v3.5.2
#    rehearsal"); this EKS path was last run end to end on the 2026-09-06/07
#    v3.4.5-era rehearsal and not re-exercised for the version bump.
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
$ArgoCdVersion = "v3.5.2"   # keep in sync with kubernetes/README.md's pinned version (exact-version pin, never "stable")
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

## Next rehearsal (short path)

The full first-time bootstrap is above. Once you have done it once, this is the condensed
loop — bring the cluster up, verify, tear it straight back down. It does not replace the
sections above; it is a checklist for someone who already knows the repo.

**Bring up**

1. `aws configure` / select the SSO profile; confirm the region (`eu-central-1` in
   `terraform.tfvars`).
2. `cd terraform/aws; terraform init; terraform plan -out=tfplan; terraform apply tfplan`.
3. `terraform output -raw configure_kubectl | Invoke-Expression`.
4. `kubectl get nodes` — the managed node group is `Ready`.
5. Install the AWS Load Balancer Controller (Bootstrap step 3 — the `helm install` block).
6. Install ArgoCD and port-forward the UI (Bootstrap step 5).
7. Bootstrap sealed-secrets and **reseal the 4 secrets for THIS cluster** (Bootstrap steps
   6 / 6a / 6b). A `SealedSecret` is bound to the sealing key of the controller that encrypted
   it — after a `terraform destroy` the ciphertexts in `kubernetes/overlays/aws/sealed/` can no
   longer be decrypted by the new cluster's controller. Every fresh ephemeral EKS needs its own
   4 files sealed against the new key.
8. Pin the image tag: `cd kubernetes/overlays/aws; kustomize edit set image
   "ghcr.io/<owner>/ahc-app=ghcr.io/<owner>/ahc-app:sha-<commit>"`.
9. `kubectl apply -f argocd/ahc-aws.yaml`, then the manual sync patch (First sync, step 8).
   No domain? Apply the HTTP-only Application patch from "Running the rehearsal without a
   domain" before that first sync.

**Verify**

10. ArgoCD `ahc-aws`: `Synced` / `Healthy` / last operation `Succeeded`, at the expected
    revision.
11. `kubectl -n ahc get pvc` — `app-media-pvc` and `app-private-pvc` reach `Bound` with **no
    bootstrap Pod**; `WaitForFirstConsumer` binds them once `ahc-app-backend` / `celery-worker`
    schedule.
12. `kubectl -n ahc get pod -o wide` — `ahc-app-backend` and `celery-worker` land on the **same
    node** on their own.
13. `kubectl -n ahc get deploy ahc-app-backend celery-worker -o jsonpath='{range .items[*]}{.metadata.name}{" nodeSelector="}{.spec.template.spec.nodeSelector}{"\n"}{end}'`
    — `nodeSelector` empty for both; co-location comes only from the
    `requiredDuringSchedulingIgnoredDuringExecution` pod affinity on
    `topologyKey: kubernetes.io/hostname` (label `colocation-group: app-private-rwo`).
14. `kubectl -n kube-system logs deploy/ebs-csi-controller -c csi-provisioner --tail=50` (and
    `-c ebs-plugin`) — no `UnauthorizedOperation` / `ec2:DescribeInstanceTypes` denials after
    new volumes are provisioned.

**Smoke**

15. `kubectl -n ahc get ingress ingress-service` — note the ALB hostname, then
    `curl.exe -f http(s)://<host>/livez` and `/readyz`.
16. Optional: trigger one real Celery task, confirm producer → Redis → worker → success.

**Then tear down immediately** — do not leave the cluster running. Follow "Teardown" below in
full.

## Teardown

**Read this before running `terraform destroy`.** The ALB and every EBS volume were created by
controllers running *inside* the cluster (the AWS Load Balancer Controller, the EBS CSI driver),
not by Terraform — they are invisible to Terraform state. Destroy the VPC/EKS cluster while they
still exist and they are orphaned: they keep billing and nothing is left that can delete them
through the normal path. **Do not run `terraform destroy` until the in-cluster controllers have
had the chance to delete what they created.** Hand-deleting an `in-use` EBS volume is a
last-resort recovery path, not part of this procedure — the ordered steps below exist so it
never comes to that.

Live-only rehearsal edits need **no separate revert step**. The HTTP-only Ingress patch, the
`ALLOWED_HOSTS="*"` ConfigMap edit and any throwaway `nodeSelector` (see "Running the rehearsal
without a domain") all sit on resources this procedure deletes anyway: the Ingress patch goes
with the `ahc-aws` Application at step 8, the ConfigMap value with the namespace's workloads at
steps 3–5, a `nodeSelector` with its Deployment at step 3. Restoring the placeholder TLS
annotations moments before the ALB is deleted would be busywork.

```powershell
$Region      = terraform -chdir=terraform/aws output -raw region
$ClusterName = terraform -chdir=terraform/aws output -raw cluster_name
$VpcId       = terraform -chdir=terraform/aws output -raw vpc_id

# 1. Delete the Ingress — this is what tells the ALB Controller to delete the ALB
kubectl -n ahc delete ingress ingress-service --ignore-not-found

# 2. Wait until the ALB is really gone (Controller deletion is async). Adjust
#    the name filter to match your cluster if needed (ALB names look like
#    k8s-ahc-ingressse-<hash>).
do {
  $albs = aws elbv2 describe-load-balancers --region $Region `
    --query "LoadBalancers[?starts_with(LoadBalancerName, 'k8s-ahc')].LoadBalancerArn" --output text
  if ($albs) { Write-Host "ALB still present, waiting..."; Start-Sleep 15 }
} while ($albs)

# 3. Remove the workloads that hold storage, so the EBS CSI driver can detach
#    and delete the volumes while it is still running
kubectl -n ahc delete deploy --all
kubectl -n ahc delete statefulset --all
kubectl -n ahc delete job --all --ignore-not-found

# 4. Confirm nothing is left mounting a volume
kubectl -n ahc get pods

# 5. Delete the PVCs (gp3 reclaimPolicy is Delete → the CSI driver deletes the
#    backing EBS volume)
kubectl -n ahc delete pvc --all

# 6. Confirm the cluster side is empty
kubectl -n ahc get pvc
kubectl get pv
kubectl get volumeattachment

# 7. Wait until the CSI-created EBS volumes are really gone
do {
  $vols = aws ec2 describe-volumes --region $Region `
    --filters "Name=tag:kubernetes.io/created-for/pvc/namespace,Values=ahc" `
    --query "Volumes[].VolumeId" --output text
  if ($vols) { Write-Host "EBS volumes still present, waiting..."; Start-Sleep 15 }
} while ($vols)

# 8. Only now remove the ArgoCD Application (nothing left for it to prune)
kubectl delete -f argocd/ahc-aws.yaml --ignore-not-found

# 9. Only now tear down the infrastructure
terraform -chdir=terraform/aws destroy

# 10. Post-destroy audit. "Clean" means nothing is left that belonged to THIS
#     cluster / VPC — not that the account has zero resources. An unrelated EKS
#     cluster, ALB, NAT gateway or Elastic IP in the same account and region is
#     normal; leave it alone. Never delete a resource just to make a line here
#     come back empty. Each query is scoped where a safe filter exists.
terraform -chdir=terraform/aws state list                       # our state file — must be empty

aws eks describe-cluster --name $ClusterName --region $Region    # expect: ResourceNotFoundException

aws elbv2 describe-load-balancers --region $Region `
  --query "LoadBalancers[?starts_with(LoadBalancerName, 'k8s-ahc')].LoadBalancerName"   # ALB Controller LBs for ns ahc

aws ec2 describe-nat-gateways --region $Region `
  --filter "Name=vpc-id,Values=$VpcId" "Name=state,Values=available" `
  --query "NatGateways[].NatGatewayId"                          # NAT still live in the (now-destroyed) VPC

aws ec2 describe-volumes --region $Region `
  --filters "Name=tag:kubernetes.io/created-for/pvc/namespace,Values=ahc" `
  --query "Volumes[].VolumeId"                                  # CSI volumes for ns ahc (same filter as step 7)

# Elastic IPs carry no reliable AHC-specific tag from the VPC module, so this
# one stays account-wide: it lists only *unassociated* addresses (the shape a
# leaked NAT EIP takes). Do NOT release an address you cannot tie to this
# stack — cross-check against the NAT gateway(s) above and the destroyed VPC.
aws ec2 describe-addresses --region $Region `
  --query "Addresses[?AssociationId==null].[AllocationId,PublicIp,Tags]"
```

The 2026-09-06/07 rehearsal teardown ran clean this way: `terraform destroy` reported **65
resources destroyed**, `terraform state list` was empty afterwards, `aws eks describe-cluster`
returned `ResourceNotFoundException`, and the ALB / NAT-gateway / CSI-volume / unassociated-EIP
checks showed nothing left for this cluster or its VPC. The account still held unrelated
resources — expected; the audit is scoped, not an account-wide emptiness assertion.

If steps 1–7 are skipped, or the cluster is destroyed before they finish, the ALB and EBS
volumes must be cleaned up by hand via the AWS console/CLI — they do not disappear on their own
and keep billing.

## AWS overlay specifics & rehearsal learnings

Everything below is EKS-specific and was found (or confirmed) during the PR #28 rehearsal on a
real cluster in `eu-central-1`. The base manifests are unchanged; the AWS behaviour lives in
`kubernetes/overlays/aws/` patches.

The 2026-09-06/07 rehearsal ran the full path end to end on commit `30c8948` — CI green, ArgoCD
`Synced` / `Healthy` / `Succeeded`, then a fresh-storage test (scale `ahc-app-backend` and
`celery-worker` to 0, delete both app PVCs, re-sync) that confirmed the fixes below, followed by
a clean teardown (65 Terraform resources destroyed, no orphaned AWS resources).

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
`certificate-arn` placeholder and an HTTPS listener, `configmap-patch.yaml` carries a placeholder
`AHC_DOMAIN` in `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS`. With `manage_dns = false` and the
placeholders left in place, the ALB never gets a valid listener — a safe resting state, but not
a running app.

**TLS/HTTPS against a real ACM certificate and a real domain was not exercised** in the
2026-09-06/07 rehearsal (no owned domain was available). That path — `manage_dns = true`,
`domain_name` set, `dns.tf` active, the real `certificate-arn` in `ingress-patch.yaml` — remains
untested end to end. Everything below is how the rehearsal reached a working `/livez` without it.

### Running the rehearsal without a domain

The 2026-09-06/07 rehearsal ran **HTTP-only, no ACM, no domain**. Two changes made that
possible. Neither was committed — `overlays/aws` stays HTTPS-shaped — and the Ingress change is
**not** a `kubectl edit`/`annotate` on the live resource: the next manual ArgoCD sync re-renders
the overlay from Git and would revert that. It goes on the `ahc-aws` **Application** instead, as
an inline kustomize patch ArgoCD re-applies on every sync.

```powershell
# 1. HTTP-only Ingress: add a kustomize patch to the Application itself, not to
#    the overlay in Git. It flips listen-ports to HTTP:80, drops the two TLS
#    annotations, and removes the placeholder host so the rule matches the
#    *.elb.amazonaws.com name the ALB answers on. --type merge deep-merges
#    spec.source, so repoURL/targetRevision/path are kept; it only adds
#    spec.source.kustomize (absent on this Application until now).
@'
spec:
  source:
    kustomize:
      patches:
        - target:
            kind: Ingress
            name: ingress-service
          patch: |-
            - op: replace
              path: /metadata/annotations/alb.ingress.kubernetes.io~1listen-ports
              value: '[{"HTTP":80}]'
            - op: remove
              path: /metadata/annotations/alb.ingress.kubernetes.io~1ssl-redirect
            - op: remove
              path: /metadata/annotations/alb.ingress.kubernetes.io~1certificate-arn
            - op: remove
              path: /spec/rules/0/host
'@ | Set-Content patch-ahc-aws-http.yaml
kubectl -n argocd patch application ahc-aws --type merge --patch-file patch-ahc-aws-http.yaml

# 2. Re-sync so ArgoCD renders the overlay with that patch applied
kubectl -n argocd patch application ahc-aws --type merge `
  -p '{"operation":{"initiatedBy":{"username":"manual"},"sync":{"revision":"main","syncStrategy":{"hook":{}}}}}'

# 3. ALLOWED_HOSTS="*": the ALB hostname is not known ahead of time, so Django
#    must accept any Host header for the smoke test. Nothing in the sync path
#    rewrites this ConfigMap value, so a direct patch is fine here.
kubectl -n ahc patch configmap ahc-app-config --type merge -p '{"data":{"ALLOWED_HOSTS":"*"}}'
kubectl -n ahc rollout restart deploy/ahc-app-backend

# 4. Smoke over plain HTTP
kubectl -n ahc get ingress ingress-service          # note the *.elb.amazonaws.com hostname
curl.exe -f http://<alb-hostname>/livez
curl.exe -f http://<alb-hostname>/readyz
```

> **`ALLOWED_HOSTS="*"` is a rehearsal shortcut, not a production recommendation.** It disables
> Django's Host-header validation entirely. Production must list the real domain(s), and the ALB
> must terminate TLS with a real ACM certificate — a path **not exercised** in this rehearsal
> (see the section above).

The `ahc-aws` Application stays `Synced` with the inline patch (it is part of the desired state
ArgoCD renders); only the `kubectl patch` on the ConfigMap shows as `OutOfSync`, which is
expected. Do **not** "resolve" that by committing `ALLOWED_HOSTS="*"` or the HTTP-only
annotations into `overlays/aws`. Both changes are undone by teardown — the Application (and its
inline patch) at "Teardown" step 8, the ConfigMap with its namespace — so there is nothing to
revert by hand.

### Node instance type & account limits

`terraform.tfvars.example` defaults `node_instance_types` to `["t3.medium"]`. During the
2026-09-06/07 rehearsal AWS rejected `t3.medium` for this account (a Free-plan / new-account
capacity or eligibility limit, not a repo problem); the run used `c7i-flex.large` set in the
**local, git-ignored** `terraform/aws/terraform.tfvars`.

- The workable instance type depends on the AWS account's limits and eligibility — expect to
  override it.
- If the default type is rejected, set `node_instance_types` in your local `terraform.tfvars`
  and re-`apply`. Do **not** commit an account-specific size into `terraform.tfvars.example`
  (and don't change that file's default without a repo-wide reason).

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

A second static check in the same job — "Assert AWS deploy stays manual (cost guardrail)" —
fails CI if `argocd/ahc-aws.yaml` ever gains a `spec.syncPolicy.automated` block, if this
workflow ever runs `terraform apply` / `terraform destroy`, or if the `bump` job ever touches
`kubernetes/overlays/aws`. It renders and validates the overlay; it never deploys it.

## Troubleshooting

See `kubernetes/README.md`'s "GitOps rehearsal" section for ArgoCD-level troubleshooting (stuck
syncs, `--server-side` apply, terminating an operation) — it applies identically here, this
overlay just points at a different cluster and Application name (`ahc-aws`).
