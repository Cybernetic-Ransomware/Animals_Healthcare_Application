import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("animals", "0007_profile_image_static_default"),
        ("veterinary", "0001_initial"),
    ]

    operations = [
        # State-only rename: db_column pins each field to its original column, so no RENAME COLUMN is issued.
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RenameField(
                    model_name="animal",
                    old_name="first_contact_vet",
                    new_name="legacy_first_contact_vet",
                ),
                migrations.RenameField(
                    model_name="animal",
                    old_name="first_contact_medical_place",
                    new_name="legacy_first_contact_medical_place",
                ),
                migrations.AlterField(
                    model_name="animal",
                    name="legacy_first_contact_vet",
                    field=models.CharField(
                        blank=True, default=None, max_length=250, null=True, db_column="first_contact_vet"
                    ),
                ),
                migrations.AlterField(
                    model_name="animal",
                    name="legacy_first_contact_medical_place",
                    field=models.CharField(
                        blank=True, default=None, max_length=250, null=True, db_column="first_contact_medical_place"
                    ),
                ),
            ],
        ),
        # New relations, physically added as first_contact_vet_id / first_contact_medical_place_id.
        migrations.AddField(
            model_name="animal",
            name="first_contact_vet",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="first_contact_for",
                to="veterinary.vet",
            ),
        ),
        migrations.AddField(
            model_name="animal",
            name="first_contact_medical_place",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="first_contact_for",
                to="veterinary.medicalplace",
            ),
        ),
    ]
