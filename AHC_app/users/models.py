from django.db import models
from django.contrib.auth.models import User
from PIL import Image

# TODO create Privilege, ProfileBackground models, import and set default


class Privilege(models.Model):
    # TODO move to homepage
    pass


class ProfileBackground(models.Model):
    pass


class ApplicationUser(User):
    email = models.EmailField()
    registration_date = models.DateField(auto_now_add=True)
    privilege_tier = models.ForeignKey(Privilege, on_delete=models.SET_DEFAULT, default=None)


class Profile(models.Model):
    user = models.OneToOneField(ApplicationUser, on_delete=models.CASCADE)
    birthdate = models.DateField(Null=True, db_index=True, default=None)
    profile_image = models.ImageField(default='profile_pics/signup.png', upload_to='profile_pics')
    profile_background = models.ForeignKey(ProfileBackground, on_delete=models.SET_DEFAULT, default=None)

    def __str__(self):
        return f'Profile of {self.user.username}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        img = Image.open(self.image.path)

        if any([img.height > 300, img.width > 300]):
            output_size = (300, 300)
            img.thumbnail(output_size)
            img.save(self.image.path)
