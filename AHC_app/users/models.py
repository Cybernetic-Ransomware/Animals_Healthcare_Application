from django.contrib.auth.models import User
from django.db import models
from homepage.models import Privilege, ProfileBackground
from PIL import Image

# TODO create Privilege, ProfileBackground models, import and set default


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    birthdate = models.DateField(null=True, db_index=True, default=None)
    profile_image = models.ImageField(
        default="profile_pics/signup.png", upload_to="profile_pics"
    )
    privilege_tier = models.ForeignKey(
        Privilege, on_delete=models.SET_NULL, null=True, default=None
    )
    profile_background = models.ForeignKey(
        ProfileBackground, on_delete=models.SET_NULL, default=None, null=True
    )

    def __str__(self):
        return f"Profile of {self.user.username}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        img = Image.open(self.profile_image.path)

        if any([img.height > 300, img.width > 300]):
            output_size = (300, 300)
            img.thumbnail(output_size)
            img.save(self.profile_image.path)
