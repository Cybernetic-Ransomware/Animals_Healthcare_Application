"""Build a read-only SQLite snapshot of one animal's health data (see ADR-12).

The Turso/libSQL driver is used only inside this module — it is never wired
into the Django ORM. Snapshot content is filtered by the requesting profile's
share categories, mirroring the tab gating on the animal profile page.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import turso
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from ahc.apps.animals.models import Animal, ShareCategory
from ahc.apps.animals.selectors import allowed_categories_for, user_can_view_animal
from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
from ahc.apps.medical_notes.models.type_measurement_notes import BiometricRecord
from ahc.apps.medical_notes.selectors import feeding_notes_for, other_history_for, timeline_for
from ahc.apps.offline_snapshots.services.schema import SCHEMA_VERSION, create_schema

if TYPE_CHECKING:
    from ahc.apps.users.models import Profile

CATEGORY_EVENT_TYPES: dict[str, tuple[str, ...]] = {
    ShareCategory.HISTORY.value: ("medical_visit",),
    ShareCategory.DIET.value: ("diet_note",),
    ShareCategory.MEDICATIONS.value: ("medicament_note",),
    ShareCategory.BIOMETRICS.value: ("biometric_record",),
    ShareCategory.VACCINATIONS.value: ("vaccination_note",),
}

FEEDING_EVENT_TYPES = ("diet_note", "medicament_note")


def _iso(value: date | datetime | None) -> str | None:
    """Serialise a date or datetime to ISO 8601; datetimes are normalised to UTC."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    return value.isoformat()


def _records_to_export(animal: Animal, allowed: set[str]) -> list[MedicalRecord]:
    records: list[MedicalRecord] = []
    for category, event_types in CATEGORY_EVENT_TYPES.items():
        if category not in allowed:
            continue
        for event_type in event_types:
            records.extend(timeline_for(animal, type_of_event=event_type))
    if ShareCategory.HISTORY.value in allowed:
        records.extend(other_history_for(animal))
    return records


def _source_revision(records: list[MedicalRecord]) -> str:
    updates = [record.date_updated for record in records if record.date_updated]
    latest = _iso(max(updates)) if updates else "empty"
    return f"{latest}:{len(records)}"


def _insert_manifest(conn: turso.Connection, animal: Animal, profile: Profile, records: list[MedicalRecord]) -> None:
    conn.execute(
        "INSERT INTO snapshot_manifest (id, animal_id, schema_version, source_revision, generated_at, generated_by,"
        " is_read_only) VALUES (1, ?, ?, ?, ?, ?, 1)",
        (str(animal.id), SCHEMA_VERSION, _source_revision(records), _iso(timezone.now()), profile.user.username),
    )


def _insert_animal(conn: turso.Connection, animal: Animal, allowed: set[str]) -> None:
    row: dict[str, str | None] = {
        "species": None,
        "breed": None,
        "sex": None,
        "birthdate": None,
        "dietary_restrictions": None,
        "first_contact_vet": None,
        "first_contact_medical_place": None,
        "last_control_visit": None,
        "next_visit_date": None,
    }
    if ShareCategory.BASIC.value in allowed:
        row["species"] = animal.species
        row["breed"] = animal.breed
        row["sex"] = animal.sex
        row["birthdate"] = _iso(animal.birthdate)
    if ShareCategory.DIET.value in allowed:
        row["dietary_restrictions"] = animal.dietary_restrictions
    if ShareCategory.VET_CONTACT.value in allowed:
        row["first_contact_vet"] = animal.first_contact_vet
        row["first_contact_medical_place"] = animal.first_contact_medical_place
        row["last_control_visit"] = _iso(animal.last_control_visit)
        row["next_visit_date"] = _iso(animal.next_visit_date)
    conn.execute(
        "INSERT INTO animal_snapshot (id, full_name, species, breed, sex, birthdate, dietary_restrictions,"
        " first_contact_vet, first_contact_medical_place, last_control_visit, next_visit_date)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (str(animal.id), animal.full_name, *row.values()),
    )


def _insert_medical_records(conn: turso.Connection, records: list[MedicalRecord]) -> None:
    for record in records:
        conn.execute(
            "INSERT INTO medical_record_snapshot (id, animal_id, date_creation, date_updated, date_event_started,"
            " date_event_ended, participants, place, short_description, full_description, type_of_event, tags_json)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(record.id),
                str(record.animal_id),  # type: ignore
                _iso(record.date_creation),
                _iso(record.date_updated),
                _iso(record.date_event_started),
                _iso(record.date_event_ended),
                record.participants,
                record.place,
                record.short_description,
                record.full_description,
                record.type_of_event,
                json.dumps(sorted(record.note_tags.names())),
            ),
        )


def _insert_feeding_notes(conn: turso.Connection, records: list[MedicalRecord]) -> None:
    for record in records:
        if record.type_of_event not in FEEDING_EVENT_TYPES:
            continue
        for note in feeding_notes_for(record):
            conn.execute(
                "INSERT INTO feeding_note_snapshot (id, medical_record_id, real_start_date, real_end_date,"
                " is_medicine, category, product_name, producer, dose_annotations, purchase_source)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    note.pk,
                    str(record.id),
                    _iso(note.real_start_date),
                    _iso(note.real_end_date),
                    int(note.is_medicine),
                    note.category,
                    note.product_name,
                    note.producer,
                    note.dose_annotations,
                    note.purchase_source,
                ),
            )


def _insert_biometrics(conn: turso.Connection, animal: Animal) -> None:
    biometrics = BiometricRecord.objects.filter(animal=animal).select_related(
        "weight_biometric_record", "height_biometric_record", "custom_biometric_record"
    )
    for biometric in biometrics:
        weight = biometric.weight_biometric_record
        height = biometric.height_biometric_record
        custom = biometric.custom_biometric_record
        conn.execute(
            "INSERT INTO biometric_snapshot (id, animal_id, related_note_id, date_updated, weight, weight_unit,"
            " height, height_unit, custom_name, custom_value, custom_unit)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                biometric.pk,
                str(animal.id),
                str(biometric.related_note_id) if biometric.related_note_id else None,  # type: ignore
                _iso(biometric.date_updated),
                str(weight.weight) if weight else None,
                weight.weight_unit_to_present if weight else None,
                str(height.height) if height else None,
                height.height_unit_to_present if height else None,
                custom.record_name if custom else None,
                custom.record_value if custom else None,
                custom.record_unit if custom else None,
            ),
        )


def _insert_attachment_metadata(conn: turso.Connection, records: list[MedicalRecord]) -> None:
    for record in records:
        for attachment in record.attachments.all():  # type: ignore
            conn.execute(
                "INSERT INTO attachment_metadata_snapshot (id, medical_record_id, file_name, description, couch_id,"
                " upload_date) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(attachment.id),
                    str(record.id),
                    attachment.file_name,
                    attachment.description,
                    attachment.couch_id,
                    _iso(attachment.upload_date),
                ),
            )


def _sanity_check(conn: turso.Connection, animal: Animal, records: list[MedicalRecord]) -> None:
    manifest = conn.execute("SELECT animal_id, schema_version FROM snapshot_manifest WHERE id = 1").fetchone()
    if manifest is None or manifest[0] != str(animal.id) or manifest[1] != SCHEMA_VERSION:
        raise RuntimeError("Snapshot manifest failed validation.")
    count_row = conn.execute("SELECT COUNT(*) FROM medical_record_snapshot").fetchone()
    if count_row is None or count_row[0] != len(records):
        raise RuntimeError(f"Snapshot contains {count_row} medical records, expected {len(records)}.")


def export_animal_snapshot(animal: Animal, profile: Profile, output_dir: Path, force: bool = False) -> Path:
    """Export the animal's data visible to the profile into animal_<uuid>.db.

    The snapshot is written to a temporary sibling file and swapped in with
    os.replace so readers never observe a partially written database.

    Raises PermissionDenied when the profile may not view the animal, and
    FileExistsError when the target file exists and force is False.
    """
    if not user_can_view_animal(profile, animal):
        raise PermissionDenied("Profile has no access to this animal.")
    allowed = allowed_categories_for(profile, animal)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    final_path = output_dir / f"animal_{animal.id}.db"
    if final_path.exists() and not force:
        raise FileExistsError(f"Snapshot file already exists: {final_path}")

    records = _records_to_export(animal, allowed)
    tmp_path = output_dir / f"animal_{animal.id}.tmp.db"
    try:
        conn = turso.connect(str(tmp_path))
        try:
            create_schema(conn)
            _insert_manifest(conn, animal, profile, records)
            _insert_animal(conn, animal, allowed)
            _insert_medical_records(conn, records)
            _insert_feeding_notes(conn, records)
            if ShareCategory.BIOMETRICS.value in allowed:
                _insert_biometrics(conn, animal)
            _insert_attachment_metadata(conn, records)
            conn.commit()
            _sanity_check(conn, animal, records)
        finally:
            conn.close()
        os.replace(tmp_path, final_path)
    finally:
        tmp_path.unlink(missing_ok=True)
    return final_path
