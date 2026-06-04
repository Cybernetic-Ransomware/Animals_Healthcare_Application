from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
from ahc.apps.medical_notes.models.type_feeding_notes import FeedingNote


@receiver(post_save, sender=FeedingNote)
def clean_orphaned_diet_records(sender, instance, **kwargs):
    related = instance.related_note
    if related is None or related.author is None:
        return
    with transaction.atomic():
        shells = MedicalRecord.objects.filter(author=related.author, type_of_event="diet_note")
        for record in shells:
            if not record.feedingnote_set.exists():
                record.delete()
