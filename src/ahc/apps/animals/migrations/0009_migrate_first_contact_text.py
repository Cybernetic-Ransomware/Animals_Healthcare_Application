from django.db import migrations


def _split_legacy_text(text):
    """Split normalized legacy contact text into (name, details), or None when it is blank.

    The first line becomes `name` (always fits, since the legacy column is at most 250 chars,
    same as `name`). The remaining lines become `details`, verbatim, so that
    `name + "\\n" + details` (or `name` alone) reconstructs the normalized text exactly —
    including an empty line right after the first, which `as_contact_text()` must round-trip.
    """
    if text is None:
        return None
    normalized = "\n".join(line.rstrip() for line in text.strip().splitlines())
    if not normalized:
        return None
    lines = normalized.split("\n")
    name = lines[0]
    details = "\n".join(lines[1:])
    return name, details


def _reuse_or_create_contact(model, *, owner_id, name, details, **extra_empty_fields):
    """Return an existing contact with identical materialized fields, or create one.

    Reuse (rather than always creating) is what makes the forward pass idempotent across a
    revert to 0008 and a re-run of 0009: any contact already produced by a previous run, or
    created manually, is matched and reused instead of duplicated.
    """
    lookup = {"owner_id": owner_id, "name": name, "details": details, "phone": "", "email": "", **extra_empty_fields}
    existing = model.objects.filter(**lookup).order_by("pk").first()
    if existing is not None:
        return existing
    return model.objects.create(**lookup)


def forward(apps, schema_editor):
    """Materialize legacy first-contact text into Vet / MedicalPlace records.

    Only animals with an owner are processed; ownerless legacy text is left untouched, as it
    cannot be assigned to anyone's contact book. An already-set FK is never overwritten, so a
    contact picked in the new UI is never replaced by a legacy-text-derived one. Legacy text
    columns are read-only here — never modified or cleared.
    """
    Animal = apps.get_model("animals", "Animal")
    Vet = apps.get_model("veterinary", "Vet")
    MedicalPlace = apps.get_model("veterinary", "MedicalPlace")

    for animal in Animal.objects.filter(owner_id__isnull=False):
        update_fields = []

        if animal.first_contact_vet_id is None:
            split = _split_legacy_text(animal.legacy_first_contact_vet)
            if split is not None:
                name, details = split
                vet = _reuse_or_create_contact(Vet, owner_id=animal.owner_id, name=name, details=details)
                animal.first_contact_vet_id = vet.pk
                update_fields.append("first_contact_vet")

        if animal.first_contact_medical_place_id is None:
            split = _split_legacy_text(animal.legacy_first_contact_medical_place)
            if split is not None:
                name, details = split
                place = _reuse_or_create_contact(
                    MedicalPlace, owner_id=animal.owner_id, name=name, details=details, address="", website=""
                )
                animal.first_contact_medical_place_id = place.pk
                update_fields.append("first_contact_medical_place")

        if update_fields:
            animal.save(update_fields=update_fields)


class Migration(migrations.Migration):
    dependencies = [
        ("animals", "0008_add_first_contact_record_fks"),
    ]

    operations = [
        # Reverse is a noop: legacy text is untouched, and a materialized contact may already be
        # shared by several animals or hand-edited in the contact book, so undoing it is unsafe.
        migrations.RunPython(forward, reverse_code=migrations.RunPython.noop),
    ]
