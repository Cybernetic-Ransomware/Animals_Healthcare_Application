import pytest

from ahc.apps.animals.models import Animal


@pytest.fixture
def animal(db, user_profile):
    _, profile = user_profile
    return Animal.objects.create(full_name="Whiskers", owner=profile)
