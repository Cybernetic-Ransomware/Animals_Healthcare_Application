from pathlib import Path
from typing import cast

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Field
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver

from ahc.apps.homepage.models import Privilege, ProfileBackground
from ahc.apps.users.models import Profile


@receiver(pre_save, sender=Profile)
def create_basic_privilege(sender, instance, **kwargs):
    if not instance.privilege_tier:
        privilege, _ = Privilege.objects.get_or_create(title="Empty Privilege")
        instance.privilege_tier = privilege


@receiver(pre_save, sender=Profile)
def create_background(sender, instance, **kwargs):
    if not instance.profile_background:
        background, _ = ProfileBackground.objects.get_or_create(title="Default Background")
        instance.profile_background = background


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, created, update_fields=None, **kwargs):
    if created:
        return
    if update_fields is not None and set(update_fields) <= {"last_login", "date_joined"}:
        return
    if hasattr(instance, "profile"):
        instance.profile.save()


@receiver(pre_delete, sender=Profile)
def remove_old_pictures_after_profile_delete(sender, instance, **kwargs):
    """Delete the profile's image once the delete transaction commits.

    Fires for both a direct Profile.delete() and a cascaded User.delete() — a
    pre_delete receiver disables Django's fast-delete optimization, so the cascade
    always materializes and deletes each Profile row individually. Deferred via
    transaction.on_commit so a rollback leaves the file in place. robust=True keeps
    a callback failure (e.g. a locked file) from propagating to the caller — the
    daily sweep is the recovery path for whatever this leaves behind.
    """
    name = instance.profile_image.name
    default = cast(Field, Profile._meta.get_field("profile_image")).get_default()
    if not name or name == default:
        return

    media_dir = Path(settings.MEDIA_ROOT) / "profile_pics" / "users"

    def _delete_committed_image() -> None:
        (media_dir / Path(name).name).unlink(missing_ok=True)

    transaction.on_commit(_delete_committed_image, robust=True)
