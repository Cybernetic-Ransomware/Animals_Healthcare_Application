import django.db.models.deletion
from django.db import migrations, models


def copy_existing_keepers(apps, schema_editor):
    """Copy rows from the legacy auto M2M table into AnimalShare with full access.

    Existing keepers retain complete visibility so there is no silent data loss.
    """
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO animals_animalshare
                (animal_id, carer_id, created, valid_until,
                 allow_basic, allow_vet_contact, allow_diet,
                 allow_medications, allow_history, allow_biometrics)
            SELECT
                animal_id,
                profile_id,
                CURRENT_TIMESTAMP,
                NULL,
                TRUE, TRUE, TRUE, TRUE, TRUE, TRUE
            FROM animals_animal_allowed_users
            """
        )


def restore_legacy_keepers(apps, schema_editor):
    """Reverse: copy AnimalShare rows back into the legacy M2M table."""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO animals_animal_allowed_users (animal_id, profile_id) "
            "SELECT animal_id, carer_id FROM animals_animalshare"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("animals", "0003_add_species_breed_sex_and_sterilization"),
        ("users", "0003_profile_pinned_animals"),
    ]

    operations = [
        migrations.CreateModel(
            name="AnimalShare",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("valid_until", models.DateField(blank=True, default=None, null=True)),
                ("allow_basic", models.BooleanField(default=False)),
                ("allow_vet_contact", models.BooleanField(default=False)),
                ("allow_diet", models.BooleanField(default=False)),
                ("allow_medications", models.BooleanField(default=False)),
                ("allow_history", models.BooleanField(default=False)),
                ("allow_biometrics", models.BooleanField(default=False)),
                (
                    "animal",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="shares",
                        to="animals.animal",
                    ),
                ),
                (
                    "carer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="received_shares",
                        to="users.profile",
                    ),
                ),
            ],
            options={"constraints": [models.UniqueConstraint(fields=["animal", "carer"], name="uniq_animal_carer_share")]},
        ),
        migrations.CreateModel(
            name="ShareDefaults",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("allow_basic", models.BooleanField(default=True)),
                ("allow_vet_contact", models.BooleanField(default=False)),
                ("allow_diet", models.BooleanField(default=False)),
                ("allow_medications", models.BooleanField(default=False)),
                ("allow_history", models.BooleanField(default=False)),
                ("allow_biometrics", models.BooleanField(default=False)),
                (
                    "profile",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="share_defaults",
                        to="users.profile",
                    ),
                ),
            ],
        ),
        # Step 1: copy existing keeper pairs into AnimalShare before touching the old table.
        migrations.RunPython(copy_existing_keepers, reverse_code=restore_legacy_keepers),
        # Step 2: tell the ORM the field now uses a through model (state only),
        # and physically drop the now-redundant auto M2M table (database only).
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="DROP TABLE animals_animal_allowed_users;",
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name="animal",
                    name="allowed_users",
                    field=models.ManyToManyField(
                        related_name="keepers",
                        through="animals.AnimalShare",
                        to="users.profile",
                    ),
                ),
            ],
        ),
    ]
