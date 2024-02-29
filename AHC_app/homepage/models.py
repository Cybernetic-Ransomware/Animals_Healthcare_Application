from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from homepage.utils import ImageGenerator


class Privilege(models.Model):
    title = models.CharField(max_length=30)
    privilege_to_delete_animal = models.BooleanField(default=False)

    # TODO: reconsider usage to simplyfy priveliges test mixins
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        raise NotImplementedError


class ProfileBackground(models.Model):
    title = models.CharField(max_length=30)
    content = models.ImageField(
        default=ImageGenerator.default_profile_image,
        upload_to="static/media/background",
    )

    # TODO: reconsider usage
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        raise NotImplementedError


# TODO: reconsider usage, currently Animal Profile is enough but can be used to manipulate images
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


# TODO: implement to allow set cronjobs from admin panel, must run shell command
class CronJob(models.Model):
    name = models.CharField(max_length=255)
    command = models.CharField(max_length=255)
    schedule = models.CharField(max_length=255)
    last_execution = models.DateTimeField(null=True, blank=True)
    next_execution = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name
