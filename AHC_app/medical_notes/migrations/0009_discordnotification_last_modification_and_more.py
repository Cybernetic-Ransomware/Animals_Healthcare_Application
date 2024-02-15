# Generated by Django 4.2.1 on 2024-02-02 12:46

import datetime

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("medical_notes", "0008_alter_medicalrecordattachment_file"),
    ]

    operations = [
        migrations.AddField(
            model_name="discordnotification",
            name="last_modification",
            field=models.DateTimeField(default=datetime.datetime(2024, 2, 2, 13, 46, 49, 356514)),
        ),
        migrations.AddField(
            model_name="emailnotification",
            name="last_modification",
            field=models.DateTimeField(default=datetime.datetime(2024, 2, 2, 13, 46, 49, 356514)),
        ),
        migrations.AddField(
            model_name="smsnotification",
            name="last_modification",
            field=models.DateTimeField(default=datetime.datetime(2024, 2, 2, 13, 46, 49, 356514)),
        ),
    ]