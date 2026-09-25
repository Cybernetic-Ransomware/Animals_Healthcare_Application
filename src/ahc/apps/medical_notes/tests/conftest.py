import pytest

from ahc.apps.animals.models import Animal
from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord


@pytest.fixture
def diet_note_shell(db, user_profile):
    """A MedicalRecord of type diet_note owned by user_profile."""
    _, profile = user_profile
    animal = Animal.objects.create(full_name="Diet Tester", owner=profile)
    return MedicalRecord.objects.create(
        animal=animal,
        author=profile,
        short_description="Diet shell",
        type_of_event="diet_note",
    )
