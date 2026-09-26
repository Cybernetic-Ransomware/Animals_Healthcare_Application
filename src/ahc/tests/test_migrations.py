import pytest
from django.core.management import call_command
from django.urls import get_resolver


@pytest.mark.integration
@pytest.mark.django_db
def test_no_missing_migrations():
    """Guards against model changes that were never captured in a migration."""
    # medical_notes only registers some models via views imported through the URLconf, so resolve it first.
    _ = get_resolver().url_patterns

    try:
        call_command("makemigrations", "--check", "--dry-run", verbosity=0)
    except SystemExit as exc:
        pytest.fail(f"makemigrations --check found unmigrated model changes (exit code {exc.code})")
