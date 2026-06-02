from __future__ import annotations

import uuid

from django.db import models

from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord


class VaccinationNote(models.Model):
    """Satellite model for vaccination records.

    Each instance is linked to a MedicalRecord shell with
    type_of_event="vaccination_note".  The shell provides the common
    medical timeline entry; this model holds vaccination-specific fields.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    related_note = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name="vaccination_records")

    vaccine_name = models.CharField(max_length=120)
    last_vaccination_date = models.DateField(null=True, blank=True, default=None)
    valid_until = models.DateField(null=True, blank=True, default=None)
    suggested_clinic = models.CharField(max_length=250, blank=True, default="")

    reminder_date = models.DateField(null=True, blank=True, default=None, db_index=True)
    reminder_sent = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.vaccine_name
