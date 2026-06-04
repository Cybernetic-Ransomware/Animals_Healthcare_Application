from pathlib import Path

from django.conf import settings
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from ahc.apps.animals.models import Animal

_ANIMALS_MEDIA_DIR = Path(settings.MEDIA_ROOT) / "profile_pics" / "animals"


@receiver(pre_delete, sender=Animal)
def remove_old_pictures_after_animal_delete(sender, instance, **kwargs):
    """Remove the animal's profile image when the Animal row is deleted.

    Targeted O(1) cleanup — kept as a signal because it fires at exactly the
    right moment. The broader orphan-image sweep (post_save full scan) has been
    moved to the daily Celery Beat task clean_orphaned_profile_images in
    celery_notifications/cron.py.
    """
    if instance.profile_image:
        image_path = _ANIMALS_MEDIA_DIR / Path(instance.profile_image.name).name
        image_path.unlink(missing_ok=True)


@receiver(post_save, sender=Animal)
def update_allowed_users(sender, instance, **kwargs):
    if instance.owner and instance.owner in instance.allowed_users.all():
        instance.allowed_users.remove(instance.owner)
