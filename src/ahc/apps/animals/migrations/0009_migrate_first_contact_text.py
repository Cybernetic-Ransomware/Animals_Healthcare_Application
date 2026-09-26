from django.db import migrations


def _split_legacy_text(text):
    """Split into (name, details) so `name + "\\n" + details` rebuilds the normalized text exactly."""
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
    """Reuse an identical existing contact instead of creating one (keeps re-running 0009 idempotent)."""
    lookup = {"owner_id": owner_id, "name": name, "details": details, "phone": "", "email": "", **extra_empty_fields}
    existing = model.objects.filter(**lookup).order_by("pk").first()
    if existing is not None:
        return existing
    return model.objects.create(**lookup)


def forward(apps, schema_editor):
    """Materialize legacy first-contact text into Vet / MedicalPlace records (no dual-write, ADR-15)."""
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
        # Reverse is a noop: undoing is unsafe once a contact may be shared or hand-edited.
        migrations.RunPython(forward, reverse_code=migrations.RunPython.noop),
    ]
