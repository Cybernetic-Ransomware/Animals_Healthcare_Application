from pathlib import Path
from typing import cast

from django.conf import settings
from django.db import transaction
from django.db.models import Field
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from ahc.apps.animals.models import Animal


@receiver(pre_delete, sender=Animal)
def remove_old_pictures_after_animal_delete(sender, instance, **kwargs):
    """Delete the animal's profile image once the delete transaction commits.

    Deferred via transaction.on_commit so a rollback leaves the file in place; the
    closure captures the basename and MEDIA_ROOT-resolved dir at call time, not the
    instance, so it respects per-test MEDIA_ROOT overrides. robust=True keeps a
    callback failure (e.g. a locked file) from propagating to the caller — the daily
    sweep is the recovery path for whatever this leaves behind.
    """
    name = instance.profile_image.name
    default = cast(Field, Animal._meta.get_field("profile_image")).get_default()
    if not name or name == default:
        return

    media_dir = Path(settings.MEDIA_ROOT) / "profile_pics" / "animals"

    def _delete_committed_image() -> None:
        (media_dir / Path(name).name).unlink(missing_ok=True)

    transaction.on_commit(_delete_committed_image, robust=True)


@receiver(post_save, sender=Animal)
def update_allowed_users(sender, instance, **kwargs):
    if instance.owner and instance.owner in instance.allowed_users.all():
        instance.allowed_users.remove(instance.owner)
