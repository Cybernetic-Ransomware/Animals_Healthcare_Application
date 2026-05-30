"""Services for feeding notification management."""

from __future__ import annotations

from django.shortcuts import get_object_or_404

from ahc.apps.medical_notes.models.type_feeding_notes import EmailNotification, FeedingNote


def create_email_notification(related_note: FeedingNote, form_instance, days_of_week_raw: list) -> EmailNotification:
    """Build a 7-element bool array from user-submitted day indices and create an EmailNotification.

    days_of_week_raw is a list of integer strings (e.g. ["0", "2", "5"]) as received from POST.
    """
    processed_days = [False] * 7
    for i in [int(day) for day in days_of_week_raw]:
        processed_days[i] = True

    form_instance.days_of_week = processed_days
    form_instance.related_note = related_note

    notify_kwargs = {key: value for key, value in form_instance.__dict__.items() if not key.startswith("_")}
    return EmailNotification.objects.create_notification(**notify_kwargs)


def toggle_notification(pk) -> EmailNotification:
    """Toggle the is_active flag of an EmailNotification and save."""
    notification = get_object_or_404(EmailNotification, pk=pk)
    notification.is_active = not notification.is_active
    notification.save()
    return notification


def delete_notification(pk) -> None:
    """Delete an EmailNotification by PK."""
    get_object_or_404(EmailNotification, pk=pk).delete()
