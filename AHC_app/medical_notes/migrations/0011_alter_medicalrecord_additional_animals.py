# Generated by Django 4.2.1 on 2023-10-04 12:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('animals', '0005_remove_biometricrecord_animal_and_more'),
        ('medical_notes', '0010_medicalrecord_additional_animals'),
    ]

    operations = [
        migrations.AlterField(
            model_name='medicalrecord',
            name='additional_animals',
            field=models.ManyToManyField(blank=True, null=True, related_name='additional_animals', to='animals.animal'),
        ),
    ]
