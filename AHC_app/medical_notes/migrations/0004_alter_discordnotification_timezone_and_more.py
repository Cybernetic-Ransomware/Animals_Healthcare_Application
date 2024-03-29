# Generated by Django 4.2.1 on 2023-11-07 14:37

import timezone_field.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        (
            "medical_notes",
            "0003_feedingnote_smsnotification_emailnotification_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="discordnotification",
            name="timezone",
            field=timezone_field.fields.TimeZoneField(default="Europe/London"),
        ),
        migrations.AlterField(
            model_name="emailnotification",
            name="timezone",
            field=timezone_field.fields.TimeZoneField(default="Europe/London"),
        ),
        migrations.AlterField(
            model_name="smsnotification",
            name="timezone",
            field=timezone_field.fields.TimeZoneField(default="Europe/London"),
        ),
    ]
