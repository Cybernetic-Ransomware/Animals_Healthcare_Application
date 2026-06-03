from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from ahc.apps.users.models import Profile

# create_basic_privilege and create_background were removed: Privilege and
# ProfileBackground raise NotImplementedError in __init__, making them
# permanently uninstantiable via the ORM. Profile.privilege_tier and
# Profile.profile_background are nullable (default=None), so a Profile
# without them is valid. Reconnect these handlers only after the homepage
# models are redesigned (see TODO in homepage/models.py).


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    if hasattr(instance, "profile"):
        instance.profile.save()
