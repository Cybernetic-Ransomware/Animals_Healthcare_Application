from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse

from .utils import ImageGenerator


class Privilege(models.Model):
    title = models.CharField(max_length=30)
    privilege_to_delete_animal = models.BooleanField(default=False)


class ProfileBackground(models.Model):
    title = models.CharField(max_length=30)
    # content = models.ImageField(default='AHC_app/static/media/background/background-1169534_1920.png',
    #                             upload_to='AHC_app/static/media/background')
    content = models.ImageField(
        default=ImageGenerator.default_profile_image,
        upload_to="static/media/background",
    )


class AnimalTitle(models.Model):
    title = models.CharField(max_length=30)
    content = models.ImageField(
        default="static/media/background/default_title.jpg",
        upload_to="static/media/animal_pic",
    )
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("article-detail", kwargs={"pk": self.pk})
