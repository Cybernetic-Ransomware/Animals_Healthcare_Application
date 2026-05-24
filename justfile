set shell := ["pwsh", "-NoLogo", "-Command"]

# Install all dependencies including dev group
install:
    uv sync

# Run all linters (ruff check, codespell, bandit)
lint:
    uv run ruff check .
    uv run codespell
    uv run bandit -r . -c pyproject.toml

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

# Start all Docker services
docker-up:
    docker-compose -f AHC_app/docker-compose.yml up -d --build

# Stop all Docker services
docker-down:
    docker-compose -f AHC_app/docker-compose.yml down

# Run pre-commit hooks on all files
precommit:
    uv run pre-commit run --all-files
