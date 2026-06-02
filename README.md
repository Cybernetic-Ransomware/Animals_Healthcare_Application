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

Pet owners and carers register animals, maintain detailed health records, and share selective access with other users. The system provides a unified timeline of medical events filtered by type and tag, diet and medication tracking, and automated reminders delivered via Discord.

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

Copy `.env.template` to `.env` and fill in the values:

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | yes | Django secret key |
| `DATABASE_URL` | yes | PostgreSQL connection string |
| `COUCH_DB_URL` | yes | CouchDB connection URL |
| `COUCH_DB_NAME` | yes | CouchDB database name |
| `CELERY_BROKER_URL` | yes | Redis broker URL |
| `CELERY_BACKEND` | yes | Celery result backend URL |
| `DISCORD_TOKEN` | no | Bot token for Discord notifications |
| `EMAIL_HOST` | no | SMTP host for e-mail notifications |
| `EMAIL_HOST_USER` | no | SMTP user |
| `EMAIL_HOST_PASSWORD` | no | SMTP password |

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
3. Install dependencies:
   ```powershell
   pip install uv
   uv sync
   ```
4. Install pre-commit hooks:
   ```powershell
   uv run pre-commit install
   ```
5. Start backing services (PostgreSQL, CouchDB, Redis, Celery):
   ```powershell
   docker compose -f docker/docker-compose.yml up -d postgres_db couch_db redis queue celery_beat
   ```
6. Run the Django dev server:
   ```powershell
   uv run python manage.py runserver
   ```

With `just` installed, steps 3–6 simplify to:
```powershell
just install
just precommit
just up
```

### Kubernetes Deploy

See [`kubernetes/`](kubernetes/) for kustomization files and secret templates.
Build and load images, then apply with `kubectl apply -k kubernetes/`.

## Testing

```powershell
# Run all tests
just test

# Unit tests only
uv run pytest -m unit

# Integration tests (requires Docker services running)
just test-integration
```

## Linting

```powershell
# Full suite: ruff format + check, ty, codespell, bandit
just lint
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

| ADR | Topic |
|---|---|
| [01](doc/01_adr_functionality.md) | Core functionality scope |
| [08](doc/08_adr_databases.md) | PostgreSQL + CouchDB + Redis |
| [09](doc/09_adr_user_data.md) | Data model — Animal fields and sharing |
| [11](doc/11_adr_frontend_interactions.md) | htmx + native `<dialog>` |

## Useful Links

- [PicoCSS](https://picocss.com/) — CSS framework
- [htmx](https://htmx.org/) — frontend interactions
- [Celery](https://docs.celeryq.dev/) — async task queue
- [uv](https://docs.astral.sh/uv/) — package manager
- [devs-mentoring.pl](https://www.devs-mentoring.pl/) — mentoring programme
