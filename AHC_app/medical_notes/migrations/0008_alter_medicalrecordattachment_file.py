# Generated by Django 4.2.1 on 2024-01-24 03:28

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("medical_notes", "0007_medicalrecordattachment_url"),
    ]

    operations = [
        migrations.AlterField(
            model_name="medicalrecordattachment",
            name="file",
            field=models.FileField(upload_to="attachments/"),
        ),
    ]
