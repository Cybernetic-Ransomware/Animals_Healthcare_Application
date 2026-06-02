## Repository structure — monorepo + GitHub Flow

### Date
`2023-06-05`

### Status
Done

### Context
A repository structure and branching strategy were needed for the project.

Repository options: monorepo vs polyrepo.
Branching options: GitFlow, GitHub Flow, GitLab Flow, trunk-based development.

### Decision
**Monorepo** — all code (Django app, Celery worker, Docker configs, Kubernetes manifests, docs) lives
in one repository. With a single developer and a small surface area, a polyrepo would add overhead
(cross-repo dependency tracking, versioned releases per service) with no benefit.

**GitHub Flow** — `main` is always deployable; feature work happens on short-lived branches merged
via pull request. GitFlow's `develop`/`release`/`hotfix` branching model would be overkill for
a one-developer project.

### Consequences
- All changes to any part of the system are visible in one history and can be correlated across layers.
- Migrations from simpler to more complex repository structures (polyrepo, GitFlow) are straightforward
  if the team or scope grows.
- The `main` branch is the production baseline; branch names follow Conventional Commits types
  (`feat/`, `fix/`, `refactor/`, etc.).

### Keywords
- GitHub, repository, monorepo, branching, GitHub Flow

### Links
*[2023-06-14]*\
[Monorepo vs polyrepo – Taby vs spacje #02](https://youtu.be/7FcbTBtlxqs)

*[2023-06-14]*\
[Git-Flow vs GitHub-Flow](https://quangnguyennd.medium.com/git-flow-vs-github-flow-620c922b2cbd)
