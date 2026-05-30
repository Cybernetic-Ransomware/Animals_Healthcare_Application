import os
from pathlib import Path

from django.conf import settings
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from ahc.apps.animals.models import Animal
from ahc.apps.users.models import Profile

_ANIMALS_MEDIA_DIR = Path(settings.MEDIA_ROOT) / "profile_pics" / "animals"


@receiver(post_save, sender=Animal)
def remove_old_pictures_after_change(sender, instance, **kwargs):
    if not _ANIMALS_MEDIA_DIR.is_dir():
        return
    animals_with_profile_images = {
        str(p).split("/")[-1] for p in Animal.objects.exclude(profile_image="").values_list("profile_image", flat=True)
    }
    for image_name in os.listdir(_ANIMALS_MEDIA_DIR):
        if image_name not in animals_with_profile_images:
            (_ANIMALS_MEDIA_DIR / image_name).unlink(missing_ok=True)


@receiver(pre_delete, sender=Animal)
def remove_old_pictures_after_animal_delete(sender, instance, **kwargs):
    if instance.profile_image:
        image_path = _ANIMALS_MEDIA_DIR / Path(instance.profile_image.name).name
        image_path.unlink(missing_ok=True)


@receiver(post_delete, sender=Profile)
def remove_old_pictures_after_user_delete(sender, instance, **kwargs):
    if not _ANIMALS_MEDIA_DIR.is_dir():
        return
    animals_with_profile_images = {
        str(p).split("/")[-1] for p in Animal.objects.exclude(profile_image="").values_list("profile_image", flat=True)
    }
    for image_name in os.listdir(_ANIMALS_MEDIA_DIR):
        if image_name not in animals_with_profile_images:
            (_ANIMALS_MEDIA_DIR / image_name).unlink(missing_ok=True)


@receiver(post_save, sender=Animal)
def update_allowed_users(sender, instance, **kwargs):
    if instance.owner and instance.owner in instance.allowed_users.all():
        instance.allowed_users.remove(instance.owner)
