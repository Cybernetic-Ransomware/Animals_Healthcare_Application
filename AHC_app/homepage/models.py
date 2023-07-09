from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse


class AnimalTitle(models.Model):
    title = models.CharField(max_length=30)
    content = models.ImageField(default='AHC_app/static/media/icons/chinchilla.png',
                                upload_to='AHC_app/static/media/animal_pic')
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('article-detail', kwargs={'pk': self.pk})
