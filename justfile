set shell := ["pwsh", "-NoLogo", "-Command"]

# List all available recipes
help:
    @just --list

# Install all dependencies including dev group
install:
    uv sync

# Run all linters (ruff check, ty, codespell, bandit)
lint:
    uv run ruff check .
    uv run ty check
    uv run codespell
    uv run bandit -r . -c pyproject.toml -q

# Format code and auto-fix lint issues
format:
    uv run ruff format .
    uv run ruff check --fix .

# Run all tests excluding slow
test:
    uv run pytest -m "not slow"

# Run only unit tests
test-unit:
    uv run pytest -m unit -v

# Run only integration tests
test-integration:
    uv run pytest -m integration -v

# Start Django development server
runserver:
    uv run python manage.py runserver

# Apply database migrations
migrate:
    uv run python manage.py migrate

# Open Django shell
shell:
    uv run python manage.py shell

# Read-only offline snapshot health report (pass --strict for non-zero exit on problems)
snapshots-check *ARGS:
    uv run python manage.py check_animal_snapshots {{ ARGS }}

# Prune superseded/stale snapshots and old download logs (accepts command flags)
snapshots-prune *ARGS:
    uv run python manage.py prune_animal_snapshots {{ ARGS }}

# Start all Docker services (full stack, with rebuild)
up:
    docker-compose --env-file .env -f docker/docker-compose.yml up -d --build

# Stop all Docker services
down:
    docker-compose --env-file .env -f docker/docker-compose.yml down

# Start only infrastructure services (Postgres, Redis, CouchDB) — no app rebuild
infra:
    docker-compose --env-file .env -f docker/docker-compose.yml up -d postgres_db redis couch_db

# Stop infrastructure services
infra-down:
    docker-compose --env-file .env -f docker/docker-compose.yml stop postgres_db redis couch_db

# Local dev: wait for healthy infra, migrate, run Django with hot-reload
dev:
    docker-compose --env-file .env -f docker/docker-compose.yml up -d --wait postgres_db redis couch_db
    uv run python manage.py migrate
    uv run python manage.py runserver

# Run pre-commit hooks on all files
precommit:
    uv run pre-commit run --all-files

# Commit with pre-commit checks and commitizen
commit:
    uv run pre-commit run && uv run cz commit

# Bump version using commitizen
bump:
    uv run cz bump
