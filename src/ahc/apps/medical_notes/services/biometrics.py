"""Service for creating BiometricRecord entries."""

from __future__ import annotations

from django.db import transaction

from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
from ahc.apps.medical_notes.models.type_measurement_notes import (
    BiometricCustomRecords,
    BiometricHeightRecords,
    BiometricRecord,
    BiometricWeightRecords,
)


def create_biometric_record(animal, related_note, record_type: str, data: dict) -> BiometricRecord:
    """Create the appropriate sub-record and link it to a parent BiometricRecord.

    record_type must be one of: "weight", "height", or a custom type.
    data is the cleaned_data dict from BiometricRecordForm.
    """
    if record_type == "weight":
        sub_record = BiometricWeightRecords.objects.create(
            weight=data["weight"],
            weight_unit_to_present=data["weight_unit_to_present"],
        )
        return BiometricRecord.objects.create(
            animal=animal,
            related_note=related_note,
            weight_biometric_record=sub_record,
        )

    if record_type == "height":
        sub_record = BiometricHeightRecords.objects.create(
            height=data["height"],
            height_unit_to_present=data["height_unit_to_present"],
        )
        return BiometricRecord.objects.create(
            animal=animal,
            related_note=related_note,
            height_biometric_record=sub_record,
        )

    sub_record = BiometricCustomRecords.objects.create(
        record_name=data["custom_name"],
        record_value=data["custom_value"],
        record_unit=data["custom_unit"],
    )
    return BiometricRecord.objects.create(
        animal=animal,
        related_note=related_note,
        custom_biometric_record=sub_record,
    )


def create_batch_biometric_records(
    author_profile,
    record_type: str,
    rows: list[tuple],
    allowed_ids: set,
) -> int:
    """Create a MedicalRecord + BiometricRecord pair for each (animal, data_dict) row.

    Rows whose animal.id is absent from allowed_ids are silently skipped — this is a
    defence-in-depth fence; the caller (view) should already have filtered rows to the
    permitted set.

    Pairs are created one after the other inside a single transaction. This ordering is
    intentional: the clean_orphaned_metric_records post_save signal on BiometricRecord
    deletes any biometric_record MedicalRecords by the same author that have no attached
    BiometricRecord at the moment of each save. Creating all notes before all biometries
    would cause the first biometry save to delete the still-empty sibling notes. Creating
    each (note, biometry) pair in sequence avoids that.

    Returns the number of pairs created.
    """
    count = 0
    with transaction.atomic():
        for animal, data_dict in rows:
            if animal.id not in allowed_ids:
                continue
            note = MedicalRecord.objects.create(
                animal=animal,
                author=author_profile,
                type_of_event="biometric_record",
                short_description=f"Measurement: {record_type}",
            )
            create_biometric_record(
                animal=animal,
                related_note=note,
                record_type=record_type,
                data=data_dict,
            )
            count += 1
    return count
