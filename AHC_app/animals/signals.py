import os

from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver
from users.models import Profile

from .models import Animal


@receiver(post_save, sender=Animal)
def remove_old_pictures_after_change(sender, instance, **kwargs):
    animals_with_profile_images = Animal.objects.exclude(profile_image="").values_list(
        "profile_image", flat=True
    )
    unused_images = os.listdir("static/media/profile_pics/animals/")

    animals_with_profile_images = [
        str(picture).split("/")[-1] for picture in animals_with_profile_images
    ]

    for image_name in unused_images:
        if image_name not in animals_with_profile_images:
            image_path = os.path.join("static/media/profile_pics/animals/", image_name)
            os.remove(image_path)


# is necessary to write tests for this one!
@receiver(pre_delete, sender=Animal)
def remove_old_pictures_after_animal_delete(sender, instance, **kwargs):
    if instance.profile_image:
        image_name = instance.profile_image.name
        image_path = os.path.join("static/media/profile_pics/animals/", image_name)
        if os.path.exists(image_path):
            os.remove(image_path)


@receiver(post_delete, sender=Profile)
def remove_old_pictures_after_user_delete(sender, instance, **kwargs):
    animals_with_profile_images = Animal.objects.exclude(profile_image="").values_list(
        "profile_image", flat=True
    )
    unused_images = os.listdir("static/media/profile_pics/animals/")

    animals_with_profile_images = [
        str(picture).split("/")[-1] for picture in animals_with_profile_images
    ]

    for image_name in unused_images:
        if image_name not in animals_with_profile_images:
            image_path = os.path.join("static/media/profile_pics/animals/", image_name)
            os.remove(image_path)


@receiver(post_save, sender=Animal)
def update_allowed_users(sender, instance, **kwargs):
    if instance.owner and instance.owner in instance.allowed_users.all():
        instance.allowed_users.remove(instance.owner)
