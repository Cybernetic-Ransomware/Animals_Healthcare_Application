# Generated by Django 4.2.1 on 2024-02-29 15:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("animals", "0001_initial"),
        ("users", "0002_profile_allow_recennt_animals_list"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="pinned_animals",
            field=models.ManyToManyField(related_name="+", to="animals.animal"),
        ),
    ]
