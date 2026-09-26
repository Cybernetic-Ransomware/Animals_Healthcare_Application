from __future__ import annotations

from django.db.models import QuerySet

from ahc.apps.veterinary.models import MedicalPlace, Vet


def vets_for(profile) -> QuerySet[Vet]:
    return Vet.objects.filter(owner=profile)


def medical_places_for(profile) -> QuerySet[MedicalPlace]:
    return MedicalPlace.objects.filter(owner=profile)


def animals_referencing(record) -> QuerySet:
    """Return every Animal (including archived/deceased ones) whose first contact is this record."""
    return record.first_contact_for.all()
