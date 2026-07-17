# Kubernetes deployment — ops runbook

GitOps layout for ArgoCD (see [ADR-13](../doc/13_adr_gitops_argocd.md)). All app images come from
`ghcr.io/cybernetic-ransomware/ahc-app`; the tag is rewritten per overlay.

## Layout

| Path | Purpose | Secrets | Applied by |
|---|---|---|---|
| `base/` | all workloads, config, PVCs, jobs | none (referenced only) | — |
| `overlays/minikube-local/` | local dev loop | plain Secrets, git-ignored | `kubectl apply -k` only — **never ArgoCD** |
| `overlays/minikube-argocd/` | GitOps rehearsal | SealedSecrets (minikube key) | `argocd/ahc-minikube-test.yaml`, manual sync |
| `overlays/home/` | production (k3s) | SealedSecrets (home key) | `argocd/ahc-home.yaml`, auto sync from `main` |

Sync waves: `-3` ConfigMap/Secrets/PVCs → `-2` Postgres/CouchDB/Redis → `-1` Sync hooks
(`ahc-migrate`, `couchdb-init`) → `0` web/celery/beat/flower → `1` Ingress → PostSync smoke test.
Migrations are a **Sync-phase** hook (not PreSync): ArgoCD orders by phase before wave, and PreSync
would run before the databases exist on a fresh cluster.

## Local run (minikube-local)

```powershell
# 1. Fill secrets from templates (once); the filled .yaml files are git-ignored
Copy-Item kubernetes/overlays/minikube-local/secrets/app-secret.yaml.template `
          kubernetes/overlays/minikube-local/secrets/app-secret.yaml
# ...same for postgres/couchdb/flower; generate SECRET_KEY with:
uv run python -c "import secrets; print(secrets.token_urlsafe(50))"

# 2. Render check, then apply
kubectl kustomize kubernetes/overlays/minikube-local
kubectl apply -k kubernetes/overlays/minikube-local

# 3. Watch
kubectl -n ahc get pods -w
kubectl -n ahc wait --for=condition=complete job/ahc-migrate --timeout=300s
kubectl -n ahc rollout status deploy/ahc-app-backend --timeout=300s

# 4. Smoke
kubectl -n ahc port-forward svc/ahc-app-backend-service 18000:8000
curl.exe -f -H "Host: localhost" http://127.0.0.1:18000/livez
curl.exe -f -H "Host: localhost" http://127.0.0.1:18000/readyz
```

**Job immutability caveat:** a plain re-apply after an image-tag change fails on the immutable Job
spec. Delete the hook jobs first (ArgoCD's `BeforeHookCreation` policy does this automatically):

```powershell
kubectl -n ahc delete job ahc-migrate couchdb-init --ignore-not-found
kubectl apply -k kubernetes/overlays/minikube-local
```

**Local image iteration:** the GHCR `prod` tag must contain the gunicorn CMD and health endpoints.
To test unmerged code, build straight into minikube and temporarily switch the overlay tag
(never commit `newTag: dev`):

```powershell
minikube image build -t ghcr.io/cybernetic-ransomware/ahc-app:dev -f docker/Dockerfile-app .
# set newTag: dev in overlays/minikube-local/kustomization.yaml, apply, revert before committing
```

## Sealing secrets (kubeseal)

Install once: `winget install kubeseal`. A SealedSecret decrypts only on the cluster whose
controller key encrypted it — minikube and home have separate `sealed/` directories, sealed from
the same plain files (keep an off-repo copy of those in a password manager).

```powershell
# against the target cluster context:
kubeseal --controller-namespace kube-system --fetch-cert > cluster.pem   # *.pem is git-ignored
Get-Content kubernetes/overlays/minikube-local/secrets/app-secret.yaml |
  kubeseal --cert cluster.pem --format yaml |
  Set-Content kubernetes/overlays/<overlay>/sealed/app-sealedsecret.yaml
# repeat for postgres-secret, couchdb-secret, flower-secret
```

If the cluster is rebuilt, the controller key is gone: re-seal everything from the plain files.

Note: kubeseal copies the input Secret's annotations into `spec.template.metadata` (the future
unsealed Secret), not onto the SealedSecret object itself. The overlays therefore carry a kustomize
patch stamping `argocd.argoproj.io/sync-wave: "-3"` on every SealedSecret — without it they would
sync at wave 0, after the databases that need them (found the hard way during the minikube
rehearsal).

## GitOps rehearsal on minikube (minikube-argocd)

```powershell
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.27.3/controller.yaml
# seal the four secrets into overlays/minikube-argocd/sealed/ (see above), commit them
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
# Pinned to the exact version this runbook was rehearsed with — a floating
# "stable" URL would change behavior without any change in this repo.
# --server-side is required: the applicationsets CRD exceeds the 256 KiB
# last-applied-configuration annotation limit of client-side apply.
$ArgoCdVersion = "v3.4.5"
kubectl apply -n argocd --server-side --force-conflicts -f "https://raw.githubusercontent.com/argoproj/argo-cd/$ArgoCdVersion/manifests/install.yaml"
kubectl apply -f argocd/ahc-minikube-test.yaml
```

Triggering a sync without the argocd CLI (equivalent of the Sync button; setting the
`operation` field is the documented kubectl-level interface):

```powershell
kubectl -n argocd patch application ahc-minikube-test --type merge -p '{"operation":{"initiatedBy":{"username":"manual"},"sync":{"revision":"<branch>","syncStrategy":{"hook":{}}}}}'
```

A sync stuck waiting on resources that can never become healthy will not stop when the
`operation` field is removed. The preferred method is `argocd app terminate-op
ahc-minikube-test`. Without the argocd CLI there is an **emergency workaround**, tested on the
pinned version above — note it reaches into the controller's internal state, not a public
interface (the Application CRD has no status subresource, so it patches the main object):

```powershell
kubectl -n argocd patch application ahc-minikube-test --type merge -p '{"status":{"operationState":{"phase":"Terminating"}}}'
```

Sync manually from the ArgoCD UI/CLI and verify waves and hooks. Before enabling automation on
home, pass the drift tests: `kubectl edit` a resource → diff shows drift; delete a Deployment →
re-sync restores it; delete a Secret → controller re-creates it from the SealedSecret.

**Testing branch code through ArgoCD (the honest path):** manifests come from the branch, but
`newTag: prod` points at an image built from an older `main` — a hybrid test proves nothing.
Publish and pin the branch image first:

1. `gh workflow run "AHC CI|CD" --ref <branch>` (workflow_dispatch publishes `sha-<commit>`
   without moving `prod`).
2. Wait for the publish job, note the `sha-<commit>` tag.
3. Set it in `overlays/minikube-argocd/kustomization.yaml` (`newTag: sha-<commit>`).
4. Commit and push to the branch — ArgoCD only sees what is in git.

Revert the pinned tag before merging. The `minikube image build` + `newTag: dev` shortcut from the
local-run section only applies to `minikube-local` (kubectl path), not to ArgoCD.

## Home cluster bootstrap (first time)

1. Install k3s (keeps default Traefik ingress and local-path default StorageClass).
2. Install ArgoCD pinned to the rehearsed version (see the rehearsal section for the exact
   command, the version variable and why `--server-side`).
3. `kubectl apply -f argocd/sealed-secrets.yaml` and wait for the controller.
4. Seal the four secrets against the home cluster into `overlays/home/sealed/`, commit to `main`.
5. Replace `ahc.example.home` in `overlays/home/{ingress-patch,configmap-patch}.yaml` with the real
   domain, commit.
6. `kubectl apply -f argocd/ahc-home.yaml` — first sync starts with **empty databases**; migrating
   data from the compose stack is a manual dump/restore.
7. Cutover note: `celery-beat` is pinned to 0 replicas in the home overlay until the
   compose/Watchtower stack is retired (two beats = duplicate Discord notifications).

## CI / image flow

`django.yml` publishes `ghcr.io/<owner>/ahc-app:prod` + `:sha-<commit>`, then the `bump` job commits
`kustomize edit set image ...:sha-<commit>` to `overlays/home/` (`[skip ci]`, serialized by a
concurrency group). ArgoCD polls `main` and syncs. The `deploy-workflow` job (Argo Workflows submit)
stays disabled until `vars.ARGO_SERVER_URL` is set — requires a self-hosted runner or tunnel.
The `workflows/` directory is synced by the `ahc-workflows` Application (`argocd/ahc-workflows.yaml`);
without ArgoCD apply it manually with `kubectl apply -f workflows/`. Manual workflow run:
`argo submit --from workflowtemplate/ahc-deploy-smoke -n argo`.

If GHCR packages are private, add a `dockerconfigjson` pull secret (sealed for home) and
`imagePullSecrets:` on every pod spec including the hook jobs.

## Backups (home overlay)

| CronJob | Schedule | What | Retention |
|---|---|---|---|
| `pg-backup` | 03:00 | `pg_dump -Fc` to `backup-data` PVC | 14 days |
| `couchdb-export` | 03:30 | `_all_docs` JSON dump — **diagnostic export, not a full backup** | 14 days |
| `files-backup` | 04:00 | tar of `app-media-pvc` + `app-private-pvc` | 14 days |

Restore: `pg_restore -h postgres-service -U $POSTGRES_USER -d $POSTGRES_DB /backup/pg-<stamp>.dump`;
CouchDB — re-PUT documents from the export or replicate back from a second instance; files —
untar into the PVCs.

Limitations (deliberate, documented): backups land on the same disk as the data (protects against
user error, not disk failure) and the CouchDB export is not attachment-complete. Follow-ups after
the testing phase: one-way CouchDB replication or PVC snapshots, and shipping copies off-host with
restic/rclone to a NAS.

## Credential hygiene

The legacy plaintext secret files contained a live Discord token and Mailtrap credentials —
**rotate both** before the first exposed deployment, and generate a fresh `SECRET_KEY` for home
(do not reuse the minikube one).
