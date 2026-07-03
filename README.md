# Animals Healthcare Application

![Python](https://img.shields.io/badge/python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-6.0-092E20?style=for-the-badge&logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![CouchDB](https://img.shields.io/badge/CouchDB-3.3-E42528?style=for-the-badge&logo=apachecouchdb&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![Ruff](https://img.shields.io/badge/Ruff-FCC21B?style=for-the-badge&logo=ruff&logoColor=black)
![Pytest](https://img.shields.io/badge/pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)
![UV](https://img.shields.io/badge/UV-DE5FE9?style=for-the-badge&logo=python&logoColor=white)

A Django monolith for managing pet health data — medical timelines, diet logs, biometric records, and scheduled notifications.

## Overview

Pet owners and carers register animals and maintain detailed health records.

Selective access can be shared with other users per data category (vet contact, diet, medications, vaccination history, biometrics).
The core of the app is a unified medical timeline, filterable by note type and tag.
Scheduled reminders for upcoming visits and vaccinations are delivered via Discord.

## Features

- Animal profiles with configurable per-category sharing between owners and carers.
- Medical timeline filtered by note type (visit, diet, medication, vaccination, biometric) and tag.
- Inline-editable vaccination records with date-based Discord reminders.
- Biometric tracking (weight, height, custom measurements) with historical charts planned.
- Diet plan management with recurring e-mail / Discord notification schedules.
- Attachment storage for medical documents via CouchDB.
- Async task processing (Celery Beat + Redis) for scheduled notifications.

## Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/) — package manager
- [just](https://just.systems/) — task runner (optional)
- Docker Desktop / Docker + Compose
- PostgreSQL 18 (managed via Docker)
- Apache CouchDB 3.3.3 (managed via Docker)
- Redis 7 (managed via Docker)

## Environment Variables

Copy `.env.template` to `.env` and fill in the values — all required variables and their descriptions are documented in the template file.

## Getting Started

### Docker Deploy

1. Clone the repository.
2. Set up the `.env` file based on the provided template.
3. Start all services:
   ```powershell
   docker compose -f docker/docker-compose.yml up -d --build
   ```

The stack exposes: Django app on `:8000`, Flower (Celery monitor) on `:5555`.

### Dev Instance

1. Clone the repository.
2. Set up the `.env` file based on the provided template.
3. Install `uv` and sync dependencies:
   ```powershell
   pip install uv
   uv sync
   ```
4. Register pre-commit hooks:
   ```powershell
   uv run pre-commit install
   ```
5. Start the dev server (starts backing services, applies migrations, runs Django):
   ```powershell
   just dev
   ```
   Or without `just`:
   ```powershell
   docker compose --env-file .env -f docker/docker-compose.yml up -d --wait postgres_db redis couch_db
   uv run python manage.py migrate
   uv run python manage.py runserver
   ```

### Kubernetes Deploy (alternative)

An alternative to Docker Compose for production-like environments.
See [`kubernetes/`](kubernetes/) for kustomization files and secret templates.
Build and load images, then apply with `kubectl apply -k kubernetes/`.

## Testing

#### Unit tests
```powershell
uv run pytest -m unit
# or
just test-unit
```

#### Integration tests
Requires Docker backing services running (`just infra`).
```powershell
uv run pytest -m integration
# or
just test-integration
```

#### All non-slow tests
```powershell
just test
```

## Linting

#### Check
```powershell
uv run ruff check .
uv run ty check
uv run codespell
uv run bandit -r src -c pyproject.toml -q
# or
just lint
```

#### Format (auto-fix)
```powershell
uv run ruff format .
uv run ruff check --fix .
# or
just format
```

#### Pre-commit hooks
Linting runs automatically on every `git commit` once hooks are installed (see Dev Instance step 4).
To run manually against all files:
```powershell
uv run pre-commit run --all-files
# or
just precommit
```

## Screenshots

> Click on an image to view full-size.

| Animal profile | Full timeline of notes |
|:---:|:---:|
| ![Animal profile](static/media/readme_examples/Animal%20profile.png) | ![Full timeline of notes](static/media/readme_examples/Full%20timeline%20of%20notes.png) |
| **Diet note details** | **User registration** |
| ![Diet note details](static/media/readme_examples/Diet%20note%20details.png) | ![User registration](static/media/readme_examples/User%20registration.png) |

## Architecture Decisions

Key decisions are documented as ADRs in [`doc/`](doc/):

| ADR | Status | Topic |
|---|---|---|
| [01](doc/01_adr_functionality.md) | In progress | Core functionality scope |
| [02](doc/02_adr_django.md) | Done | Web framework — Django |
| [03](doc/03_adr_monolit.md) | Done | Architecture — monolith |
| [04](doc/04_adr_monorepo.md) | Done | Repository structure — monorepo + GitHub Flow |
| [05](doc/05_adr_matlibplot.md) | Proposed | Charts — Matplotlib → Chart.js |
| [06](doc/06_adr_html_template.md) | Done | CSS framework — PicoCSS |
| [07](doc/07_adr_drf.md) | Proposed | API framework — DRF |
| [08](doc/08_adr_databases.md) | In progress | Databases — PostgreSQL + CouchDB + Redis |
| [09](doc/09_adr_user_data.md) | In progress | Data model — Animal fields and sharing |
| [10](doc/10_adr_notification_trigger.md) | In progress | Notifications — Celery Beat + Background Tasks |
| [11](doc/11_adr_frontend_interactions.md) | Done | Frontend interactions — htmx + native `<dialog>` |
| [12](doc/12_adr_turso_offline_snapshots.md) | In progress | Offline snapshots — Turso/libSQL read-only cache |

## Useful Links

- [PicoCSS](https://picocss.com/) — CSS framework
- [htmx](https://htmx.org/) — frontend interactions
- [Celery](https://docs.celeryq.dev/) — async task queue
- [uv](https://docs.astral.sh/uv/) — package manager
- [devs-mentoring.pl](https://www.devs-mentoring.pl/) — mentoring programme
