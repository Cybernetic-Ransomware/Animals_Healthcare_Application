from django.db import models
from django.contrib.auth.models import User
from PIL import Image


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    registration_date = models.DateField(auto_now_add=True)
    image = models.ImageField(default='profile_pics/signup.png', upload_to='profile_pics')

    def __str__(self):
        return f'Profile of {self.user.username}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        img = Image.open(self.image.path)

        if any([img.height > 300, img.width > 300]):
            output_size = (300, 300)
            img.thumbnail(output_size)
            img.save(self.image.path)
