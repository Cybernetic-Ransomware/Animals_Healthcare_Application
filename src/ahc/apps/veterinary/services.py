from __future__ import annotations

from typing import overload

from ahc.apps.veterinary.models import ContactRecord, MedicalPlace, Vet

_COMMON_CONTACT_FIELDS = ("name", "phone", "email", "details")
_MEDICAL_PLACE_EXTRA_FIELDS = ("address", "website")


def create_contact(owner, form) -> ContactRecord:
    """Owner is set on the unsaved instance before save(), so form input can never choose it."""
    record = form.save(commit=False)
    record.owner = owner
    record.save()
    return record


def delete_contact(record: ContactRecord) -> None:
    """Referencing animals keep existing: SET_NULL clears their first-contact FK instead."""
    record.delete()


@overload
def copy_contact_to(record: Vet, new_owner) -> Vet: ...
@overload
def copy_contact_to(record: MedicalPlace, new_owner) -> MedicalPlace: ...
def copy_contact_to(record: ContactRecord, new_owner) -> ContactRecord:
    """Reuse an identical contact of new_owner, or create a copy (ADR-15 C9).

    Identity is every materialized field (never just `name`, D14), matching the reuse rule
    from migration 0009 step 3: `.filter(**lookup).order_by("pk").first()`. The original
    record is left untouched under its previous owner.
    """
    model = type(record)
    extra_fields = _MEDICAL_PLACE_EXTRA_FIELDS if isinstance(record, MedicalPlace) else ()
    lookup = {field: getattr(record, field) for field in (*_COMMON_CONTACT_FIELDS, *extra_fields)}
    lookup["owner"] = new_owner

    existing = model.objects.filter(**lookup).order_by("pk").first()
    if existing is not None:
        return existing
    return model.objects.create(**lookup)
