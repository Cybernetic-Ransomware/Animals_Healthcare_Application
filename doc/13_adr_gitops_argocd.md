## GitOps deployment with ArgoCD

### Date:
`2026-07-16`

### Status
In-building

### Context
Production deployment is pull-based Watchtower polling the `prod` image tag on a docker-compose stack.
The `kubernetes/` manifests were a leftover from a local minikube workflow: `imagePullPolicy: Never`,
image tarballs committed under `kubernetes/tars/`, no probes, no namespace, broken Service selectors,
ephemeral Postgres storage, plaintext secret files (git-ignored) and no way to run Django migrations
inside the cluster. Deploying that state through any GitOps tool would faithfully reproduce every bug.

The goal is a declarative deployment where git is the single source of truth, the target being a
single-node k3s cluster on the home server, with local minikube used for rehearsal.

### Decision
1. **ArgoCD** syncs `kubernetes/overlays/home` from `main`. CI never talks to the cluster; it pushes
   the image to GHCR and commits a kustomize image-tag bump (`sha-<commit>`) to the home overlay,
   serialized by a GitHub Actions concurrency group. ArgoCD picks up the git diff.
2. **Kustomize layout**: `kubernetes/base` plus three overlays:
   - `minikube-local` — plain git-ignored Secrets, `kubectl apply -k` only (never an ArgoCD source,
     because ArgoCD checks out the repo and the ignored files are absent there);
   - `minikube-argocd` — SealedSecrets encrypted for the local minikube controller, used by the
     manual-sync `ahc-minikube-test` Application to rehearse the full GitOps loop;
   - `home` — SealedSecrets encrypted for the home cluster, CI-managed image tag, backups, smoke test.
3. **Sync phasing**: ArgoCD orders resources by phase first and only then by wave, so a PreSync
   migration hook would run before the databases exist on a fresh cluster. Migrations and CouchDB
   database creation are therefore **Sync-phase hooks at wave -1**, after ConfigMaps/Secrets/PVCs
   (wave -3) and the data stores (wave -2), before the app workloads (wave 0) and Ingress (wave 1).
   The smoke test is PostSync. Outside ArgoCD the jobs guard themselves with wait initContainers.
4. **Secrets**: Bitnami **Sealed Secrets**. Only true secrets are encrypted (`ahc-app-secrets`,
   `postgres-credentials`, `couchdb-credentials`, `flower-secrets`); everything else lives in the
   `ahc-app-config` ConfigMap for readable diffs. Credentials are never duplicated across secrets —
   the app maps `DB_*` variables from `postgres-credentials` via `secretKeyRef`. A SealedSecret is
   bound to one controller's private key: minikube and home have separate `sealed/` directories.
5. **Probes**: split endpoints. `/livez` has no dependencies (liveness + startup), `/readyz` runs
   `SELECT 1` against Postgres (readiness). CouchDB is deliberately outside `/readyz`: its outage
   degrades attachments, not the whole application.
6. **Data stores**: StatefulSets with volumeClaimTemplates. Postgres 18 mounts the volume at
   `/var/lib/postgresql` (the image keeps PGDATA in a versioned subdirectory since 18). Application
   file storage gets its own PVCs: `app-media-pvc` (upload dirs mounted via subPath so committed
   icons stay visible) and `app-private-pvc` shared by web and the Celery worker (offline snapshots).
7. **Migrations as a Job**, `makemigrations` removed from every deploy path; `collectstatic` runs in
   a web-pod initContainer writing to an emptyDir shared with gunicorn (ManifestStaticFilesStorage).
8. **CI → cluster reachability**: GitHub-hosted runners cannot reach the home server, so the deploy
   signal is ArgoCD polling git (option A). The `ahc-deploy-smoke` Argo WorkflowTemplate is committed
   for manual runs, and the CI submit step is gated on `vars.ARGO_SERVER_URL` (self-disabled until a
   self-hosted runner or tunnel exists). The workflow first waits until the Deployment references
   the expected `image-tag` — otherwise a CI-triggered run could bless a stale rollout that ArgoCD
   has not synced yet.
9. **Data-loss guards**: the `ahc` Namespace carries `Prune=confirm,Delete=confirm` and the data
   PVCs (`app-media-pvc`, `app-private-pvc`, `backup-data`) carry `Prune=false,Delete=false`, so
   automated prune cannot silently remove them. The app image runs as uid 1000, and hostPath-backed
   provisioners ignore `fsGroup`, so web/celery pods run a root `prepare-storage` initContainer
   (mkdir + guarded chown) before the app touches the volumes.

Rejected alternatives: Helm (kustomize already in place, no templating need), ArgoCD Image Updater
(extra controller; CI commit is simpler and auditable), External Secrets Operator (requires an
external secret store), SOPS/KSOPS (requires an ArgoCD plugin; kubeseal is plain kubectl-side).

### Consequences
- Git history becomes the deployment history; rollback is `git revert` of a bump commit.
- The Watchtower compose stack keeps running during the transition. Two live Celery beat schedulers
  would duplicate Discord notifications, so the home overlay pins `celery-beat` to 0 replicas until
  cutover.
- The first sync starts with **empty databases** — migrating data from the compose stack is a
  separate manual dump/restore operation.
- Backups: nightly `pg_dump`, a CouchDB **diagnostic export** (`_all_docs`; a real backup is one-way
  replication or a PVC snapshot — follow-up), and tar archives of the file PVCs. All land on a PVC on
  the same disk, which protects against user error, not disk failure; shipping copies off-host
  (restic/rclone to a NAS) is a post-testing follow-up.
- Application PVCs are ReadWriteOnce, which is fine on a single node; a multi-node cluster would need
  RWX or object storage.
- Losing the sealed-secrets controller key (cluster rebuild) invalidates all SealedSecrets; the
  git-ignored plain files (kept in a password manager) are the re-sealing source.

### Keywords
- ArgoCD,
- GitOps,
- kustomize,
- sealed-secrets,
- sync-wave,
- k3s.

### Links
- [ADR-08](08_adr_databases.md) — database responsibilities (PostgreSQL / CouchDB / Redis).
- [ADR-12](12_adr_turso_offline_snapshots.md) — offline snapshots stored under PRIVATE_STORAGE_ROOT.
- [kubernetes/README.md](../kubernetes/README.md) — operational runbook.
- [ArgoCD sync phases and waves](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/).
- [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets).
