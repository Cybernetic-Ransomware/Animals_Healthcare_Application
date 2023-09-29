# Generated by Django 4.2.1 on 2023-09-27 09:02

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('animals', '0005_remove_biometricrecord_animal_and_more'),
        ('medical_notes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CurrentMedicine',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('food_type', models.CharField(max_length=50)),
                ('name', models.CharField(max_length=80)),
                ('producer', models.CharField(max_length=120)),
                ('description', models.CharField(max_length=250)),
                ('frequency_description', models.CharField(max_length=250)),
                ('notifications_is_active', models.BooleanField(default=False)),
                ('notification_form', models.CharField(max_length=50)),
                ('notification_message', models.CharField(max_length=2500)),
                ('notification_frequency_interval', models.DurationField(blank=True, null=True)),
                ('animal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='animals.animal')),
            ],
        ),
        migrations.CreateModel(
            name='CurrentDiet',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('food_type', models.CharField(max_length=50)),
                ('name', models.CharField(max_length=80)),
                ('producer', models.CharField(max_length=120)),
                ('description', models.CharField(max_length=250)),
                ('animal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='animals.animal')),
            ],
        ),
        migrations.CreateModel(
            name='BiometricRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('height', models.IntegerField(default=0)),
                ('height_unit_to_present', models.CharField(default='g', max_length=3)),
                ('height_date_updated', models.DateTimeField(auto_now_add=True)),
                ('weight', models.IntegerField(default=0)),
                ('weight_unit_to_presen', models.CharField(default='mm', max_length=3)),
                ('weight_date_updated', models.DateTimeField(auto_now_add=True)),
                ('animal', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='animals.animal')),
            ],
        ),
        migrations.CreateModel(
            name='BiometricCustomRecords',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('record_name', models.CharField(max_length=30)),
                ('record_value', models.CharField(max_length=255)),
                ('biometric_record', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='medical_notes.biometricrecord')),
            ],
        ),
    ]