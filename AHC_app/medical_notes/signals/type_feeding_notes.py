from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from medical_notes.models.type_feeding_notes import FeedingNote
from users.models import Profile as UserProfile


@receiver(post_save, sender=FeedingNote)
def clean_orphaned_diet_records(sender, instance, **kwargs):
    user_profile = UserProfile.objects.get(id=instance.related_note.author.id)
    with transaction.atomic():
        orphaned_notes = FeedingNote.objects.filter(
            author=user_profile, related_note=None
        )
        orphaned_notes.delete()
