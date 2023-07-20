from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from homepage.models import Privilege, ProfileBackground

from .models import Profile


@receiver(pre_save, sender=Profile)
def create_basic_privelige(sender, instance, **kwargs):
    if not instance.privilege_tier:
        privilege, _ = Privilege.objects.get_or_create(title="Empty Privilage")
        instance.privilege_tier = privilege


@receiver(pre_save, sender=Profile)
def create_background(sender, instance, **kwargs):
    if not instance.profile_background:
        background, _ = ProfileBackground.objects.get_or_create(
            title="Default Background"
        )
        instance.profile_background = background


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        background, _ = ProfileBackground.objects.get_or_create(
            title="Default Background"
        )
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()
