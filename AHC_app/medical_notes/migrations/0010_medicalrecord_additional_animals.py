# Generated by Django 4.2.1 on 2023-10-04 12:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('animals', '0005_remove_biometricrecord_animal_and_more'),
        ('medical_notes', '0009_medicalrecord_author'),
    ]

    operations = [
        migrations.AddField(
            model_name='medicalrecord',
            name='additional_animals',
            field=models.ManyToManyField(related_name='additional_animals', to='animals.animal'),
        ),
    ]
