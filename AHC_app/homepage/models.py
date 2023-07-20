from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import models
from django.urls import reverse
from PIL import Image


# TODO: przerzuc do nowego pliku 'utils.py'
class ImageGenerator:
    @staticmethod
    def generate_black_image(width, height):
        image = Image.new("RGB", (width, height), (0, 0, 0))
        image_io = BytesIO()
        image.save(image_io, format="JPEG")
        return InMemoryUploadedFile(
            image_io, None, "black.jpg", "image/jpeg", image_io.tell(), None
        )

    @staticmethod
    def default_profile_image():
        width, height = 100, 100
        return ImageGenerator.generate_black_image(width, height)


class Privilege(models.Model):
    title = models.CharField(max_length=30)
    privelage_to_delete_animal = models.BooleanField(default=False)


class ProfileBackground(models.Model):
    title = models.CharField(max_length=30)
    # content = models.ImageField(default='AHC_app/static/media/background/background-1169534_1920.png',
    #                             upload_to='AHC_app/static/media/background')
    # TODO: sprawdż ścieżki przy pozostałych statycznych obrazach
    content = models.ImageField(
        default=ImageGenerator.default_profile_image(),
        upload_to="static/media/background",
    )


class AnimalTitle(models.Model):
    title = models.CharField(max_length=30)
    content = models.ImageField(
        default="AHC_app/static/media/icons/chinchilla.png",
        upload_to="AHC_app/static/media/animal_pic",
    )
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("article-detail", kwargs={"pk": self.pk})
