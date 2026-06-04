"""Read-only selectors for the medical_notes app.

All functions are side-effect free: they only query the database and return
values. Views, services, and mixins should call these instead of writing
inline ORM queries.
"""

from __future__ import annotations

from datetime import date, datetime

from django.db.models import DateTimeField as _DateTimeField
from django.db.models import QuerySet
from django.utils import timezone

from ahc.apps.animals.selectors import animals_visible_to, user_can_access_animal
from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord, MedicalRecordAttachment


def animal_choices_for(profile, exclude_id=None) -> list[tuple]:
    """Return (id, full_name) pairs for animals accessible to the profile.

    Optionally excludes one animal by UUID (used when the animal is already
    the primary animal on a note).
    """
    queryset = animals_visible_to(profile)
    if exclude_id is not None:
        queryset = queryset.exclude(id=exclude_id)
    return [(animal.id, animal.full_name) for animal in queryset]


def timeline_for(
    animal,
    type_of_event: str | None = None,
    tag_name: str | None = None,
) -> QuerySet[MedicalRecord]:
    """Return MedicalRecords for an animal, optionally filtered by type or tag.

    Results are prefetch_related for attachments. Ordering and timezone
    localisation remain the caller's responsibility (presentation logic).
    """
    queryset = MedicalRecord.objects.filter(animal=animal).prefetch_related("attachments")
    if type_of_event:
        queryset = queryset.filter(type_of_event=type_of_event)
    if tag_name:
        queryset = queryset.filter(note_tags__slug=tag_name)
    return queryset


def available_months_for(
    animal,
    type_of_event: str | None = None,
    tag_name: str | None = None,
) -> list:
    """Return distinct months (newest first) for which the animal has records.

    Months are computed in the active timezone so they match what the template
    renders via ``|date:"Y-m"``.  The returned list contains aware datetime
    objects truncated to month precision (day=1, time=midnight).
    """
    return list(
        timeline_for(animal, type_of_event=type_of_event, tag_name=tag_name).datetimes(
            "date_creation",
            "month",
            order="DESC",
            tzinfo=timezone.get_current_timezone(),
        )
    )


def page_of_month(
    queryset: QuerySet,
    target_month: date,
    per_page: int,
    date_field: str = "date_creation",
) -> int:
    """Return the 1-based page number (newest-first order) containing target_month.

    Counts how many records fall strictly after target_month (i.e. their date
    is >= the first day of the following month), then divides by per_page.
    Works for both DateTimeField (boundary is an aware local datetime) and
    DateField (boundary is a plain date).

    Pass the same ordered+filtered queryset used for pagination so that the
    count is consistent with the actual pages produced.
    """
    if target_month.month == 12:
        first_of_next = date(target_month.year + 1, 1, 1)
    else:
        first_of_next = date(target_month.year, target_month.month + 1, 1)

    model_field = queryset.model._meta.get_field(date_field)
    if isinstance(model_field, _DateTimeField):
        tz = timezone.get_current_timezone()
        boundary = timezone.make_aware(
            datetime(first_of_next.year, first_of_next.month, first_of_next.day, 0, 0, 0),
            tz,
        )
    else:
        boundary = first_of_next

    newer = queryset.filter(**{f"{date_field}__gte": boundary}).count()
    return newer // per_page + 1


def feeding_notes_for(medical_record) -> QuerySet:
    """Return all FeedingNotes linked to the given MedicalRecord."""
    from ahc.apps.medical_notes.models.type_feeding_notes import FeedingNote

    return FeedingNote.objects.filter(related_note=medical_record)


def notifications_for_feednote(feednote_pk) -> QuerySet:
    """Return EmailNotifications linked to a specific FeedingNote PK."""
    from ahc.apps.medical_notes.models.type_feeding_notes import EmailNotification

    return EmailNotification.objects.filter(related_note=feednote_pk)


def notifications_for_mednote(mednote_uuid) -> QuerySet:
    """Return EmailNotifications reachable through FeedingNotes of a MedicalRecord."""
    from ahc.apps.medical_notes.models.type_feeding_notes import EmailNotification, FeedingNote

    feednotes = FeedingNote.objects.filter(related_note=mednote_uuid)
    return EmailNotification.objects.filter(related_note__in=feednotes).order_by("-last_modification")


def medication_notes_for(animal) -> QuerySet[MedicalRecord]:
    """Return MedicalRecords of type medicament_note for an animal.

    Used by the Medications tab. Ordered newest first.
    """
    return (
        MedicalRecord.objects.filter(animal=animal, type_of_event="medicament_note")
        .prefetch_related("attachments")
        .order_by("-date_creation")
    )


def other_records_for(animal) -> QuerySet[MedicalRecord]:
    """Return MedicalRecords for an animal, excluding types shown on specialised tabs.

    Excludes medical_visit (Vet), diet_note (Diet), medicament_note (Medications),
    and vaccination_note (Vaccinations).
    Results are prefetch_related for attachments and ordered newest first.
    """
    return (
        MedicalRecord.objects.filter(animal=animal)
        .exclude(type_of_event__in=["medical_visit", "diet_note", "medicament_note", "vaccination_note"])
        .prefetch_related("attachments")
        .order_by("-date_creation")
    )


def other_history_for(animal) -> QuerySet[MedicalRecord]:
    """Return general (non-biometric) MedicalRecords for the Notes tab history section.

    Covers fast_note and other_user_note; excludes biometric_record, medical_visit,
    diet_note, medicament_note, and vaccination_note.
    """
    return (
        MedicalRecord.objects.filter(animal=animal)
        .exclude(
            type_of_event__in=[
                "medical_visit",
                "diet_note",
                "medicament_note",
                "biometric_record",
                "vaccination_note",
            ]
        )
        .prefetch_related("attachments")
        .order_by("-date_creation")
    )


def biometric_records_for(animal) -> QuerySet[MedicalRecord]:
    """Return biometric_record MedicalRecords for the Notes tab biometrics section."""
    return (
        MedicalRecord.objects.filter(animal=animal, type_of_event="biometric_record")
        .prefetch_related("attachments")
        .order_by("-date_creation")
    )


def is_note_author(profile, note: MedicalRecord) -> bool:
    """Return True if the profile is the author of the note."""
    return note.author == profile


def is_attachment_author(profile, attachment: MedicalRecordAttachment) -> bool:
    """Return True if the profile authored the note that owns this attachment."""
    return attachment.medical_record.author == profile


def can_access_note_animal(profile, note: MedicalRecord) -> bool:
    """Return True if the profile is owner or keeper of the animal linked to the note."""
    return user_can_access_animal(profile, note.animal)


def vaccination_notes_for(animal) -> QuerySet:
    """Return VaccinationNotes for an animal, ordered by valid_until (soonest first).

    Records without a valid_until date are placed last.
    """
    from ahc.apps.medical_notes.models.type_vaccination_notes import VaccinationNote

    return (
        VaccinationNote.objects.filter(related_note__animal=animal)
        .select_related("related_note")
        .order_by("valid_until", "reminder_date")
    )


def is_author_of_any_note(profile) -> bool:
    """Return True if the profile has authored at least one MedicalRecord."""
    return MedicalRecord.objects.filter(author=profile).exists()


def due_vaccination_reminders(on_date: date) -> QuerySet:
    """Return VaccinationNotes whose reminder_date is today or overdue and not yet sent.

    Used by the daily Celery Beat task to dispatch Discord notifications.
    """
    from ahc.apps.medical_notes.models.type_vaccination_notes import VaccinationNote

    return (
        VaccinationNote.objects.filter(reminder_date__lte=on_date, reminder_sent=False)
        .select_related("related_note__animal__owner__user")
        .exclude(reminder_date=None)
    )
