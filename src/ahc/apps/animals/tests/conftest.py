from datetime import date

import pytest

from ahc.apps.animals.models import Animal


@pytest.fixture
def animal(db, user_profile):
    _, profile = user_profile
    return Animal.objects.create(full_name="Whiskers", owner=profile)


@pytest.fixture
def deceased_animal(db, user_profile):
    _, profile = user_profile
    return Animal.objects.create(full_name="Passed", owner=profile, date_of_death=date(2024, 3, 15))
