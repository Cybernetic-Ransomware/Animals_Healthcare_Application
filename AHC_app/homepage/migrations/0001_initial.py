# Generated by Django 4.2.1 on 2023-10-12 07:43

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import homepage.utils


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Privilege',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=30)),
                ('privilege_to_delete_animal', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='ProfileBackground',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=30)),
                ('content', models.ImageField(default=homepage.utils.ImageGenerator.default_profile_image, upload_to='static/media/background')),
            ],
        ),
        migrations.CreateModel(
            name='AnimalTitle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=30)),
                ('content', models.ImageField(default='static/media/background/default_title.jpg', upload_to='static/media/animal_pic')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
