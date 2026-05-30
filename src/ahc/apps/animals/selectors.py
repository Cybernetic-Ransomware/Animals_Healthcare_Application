from __future__ import annotations

from django.db.models import Q, QuerySet

from ahc.apps.animals.models import Animal


def animals_visible_to(profile) -> QuerySet[Animal]:
    """Return all animals accessible to the given profile (owner or keeper)."""
    return Animal.objects.filter(Q(owner=profile) | Q(allowed_users=profile)).order_by("-creation_date")


def user_can_access_animal(profile, animal: Animal) -> bool:
    """Return True if the profile is the owner or one of the allowed_users of the animal."""
    if animal.owner == profile:
        return True
    return animal.allowed_users.filter(pk=profile.pk).exists()


def is_animal_owner(profile, animal: Animal) -> bool:
    """Return True if the profile is the owner of the animal."""
    return animal.owner == profile


def is_pinned(profile, animal: Animal) -> bool:
    """Return True if the animal is currently pinned by the given profile."""
    return profile.pinned_animals.filter(pk=animal.pk).exists()


def recent_records_for(animal: Animal, limit: int = 5) -> QuerySet:
    """Return the most recent MedicalRecords for the animal, newest first."""
    from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord

    return MedicalRecord.objects.filter(animal=animal).order_by("-date_creation")[:limit]
