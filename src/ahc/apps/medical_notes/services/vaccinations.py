"""Services for VaccinationNote creation, update, and deletion.

Each vaccination note is composed of two rows:
- A MedicalRecord shell (type_of_event="vaccination_note") that places the
  record on the common medical timeline.
- A VaccinationNote satellite that holds vaccination-specific fields.

Deleting a VaccinationNote also removes its shell via this service
(the shell is not useful without the satellite).
"""

from __future__ import annotations

from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
from ahc.apps.medical_notes.models.type_vaccination_notes import VaccinationNote


def create_vaccination_note(author_profile, animal, form) -> VaccinationNote:
    """Create a MedicalRecord shell and a linked VaccinationNote from a validated form."""
    vaccine_name: str = form.cleaned_data["vaccine_name"]

    shell = MedicalRecord.objects.create(
        animal=animal,
        author=author_profile,
        type_of_event="vaccination_note",
        short_description=vaccine_name,
    )

    vaccination: VaccinationNote = form.save(commit=False)
    vaccination.related_note = shell
    vaccination.save()
    return vaccination


def update_vaccination_note(vaccination: VaccinationNote, form) -> VaccinationNote:
    """Apply validated form data to an existing VaccinationNote.

    Synchronises the shell's short_description when vaccine_name changes.
    Preserves reminder_sent — it is reset to False only when reminder_date changes,
    so the daily cron can re-send if the owner reschedules.
    """
    old_reminder_date = vaccination.reminder_date
    new_reminder_date = form.cleaned_data.get("reminder_date")

    updated: VaccinationNote = form.save(commit=False)
    updated.pk = vaccination.pk
    updated.related_note = vaccination.related_note
    updated.id = vaccination.id

    if old_reminder_date != new_reminder_date:
        updated.reminder_sent = False
    else:
        updated.reminder_sent = vaccination.reminder_sent

    new_vaccine_name: str = form.cleaned_data["vaccine_name"]
    if new_vaccine_name != vaccination.related_note.short_description:
        vaccination.related_note.short_description = new_vaccine_name
        vaccination.related_note.save(update_fields=["short_description"])

    updated.save()
    return updated


def delete_vaccination_note(vaccination: VaccinationNote) -> None:
    """Delete the satellite and its MedicalRecord shell."""
    shell: MedicalRecord = vaccination.related_note
    vaccination.delete()
    shell.delete()
