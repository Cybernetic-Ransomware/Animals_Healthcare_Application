# Generated by Django 4.2.1 on 2023-10-05 12:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('medical_notes', '0012_alter_medicalrecord_additional_animals'),
    ]

    operations = [
        migrations.CreateModel(
            name='BiometricHeightRecords',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('height', models.IntegerField(default=0)),
                ('height_unit_to_present', models.CharField(default='g', max_length=3)),
            ],
        ),
        migrations.CreateModel(
            name='BiometricWeightRecords',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('weight', models.IntegerField(default=0)),
                ('weight_unit_to_present', models.CharField(default='mm', max_length=3)),
            ],
        ),
        migrations.RenameField(
            model_name='biometricrecord',
            old_name='height_date_updated',
            new_name='date_updated',
        ),
        migrations.RemoveField(
            model_name='biometriccustomrecords',
            name='biometric_record',
        ),
        migrations.RemoveField(
            model_name='biometriccustomrecords',
            name='creation_date',
        ),
        migrations.RemoveField(
            model_name='biometricrecord',
            name='height',
        ),
        migrations.RemoveField(
            model_name='biometricrecord',
            name='height_unit_to_present',
        ),
        migrations.RemoveField(
            model_name='biometricrecord',
            name='weight',
        ),
        migrations.RemoveField(
            model_name='biometricrecord',
            name='weight_date_updated',
        ),
        migrations.RemoveField(
            model_name='biometricrecord',
            name='weight_unit_to_presen',
        ),
        migrations.AddField(
            model_name='biometriccustomrecords',
            name='record_unit',
            field=models.CharField(default='non_unit', max_length=12),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='biometricrecord',
            name='custom_biometric_record',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='medical_notes.biometriccustomrecords'),
        ),
        migrations.AddField(
            model_name='biometricrecord',
            name='related_note',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='medical_notes.medicalrecord'),
        ),
        migrations.RunSQL('ALTER TABLE medical_notes_biometriccustomrecords DROP COLUMN id CASCADE;'),
        migrations.RunSQL('ALTER TABLE medical_notes_biometriccustomrecords ADD COLUMN id SERIAL PRIMARY KEY;'),
        migrations.RunSQL('ALTER TABLE medical_notes_biometricrecord DROP COLUMN id CASCADE;'),
        migrations.RunSQL('ALTER TABLE medical_notes_biometricrecord ADD COLUMN id SERIAL PRIMARY KEY;'),

        migrations.AddField(
            model_name='biometricrecord',
            name='height_biometric_record',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='medical_notes.biometricweightrecords'),
        ),
        migrations.AddField(
            model_name='biometricrecord',
            name='weight_biometric_record',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='medical_notes.biometricheightrecords'),
        ),
    ]