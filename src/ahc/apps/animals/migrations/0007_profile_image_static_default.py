from django.db import migrations, models

OLD_DEFAULT = "profile_pics/pet-care.png"


def blank_out_default_profile_image(apps, schema_editor):
    Animal = apps.get_model("animals", "Animal")
    Animal.objects.filter(profile_image=OLD_DEFAULT).update(profile_image="")


def restore_default_profile_image(apps, schema_editor):
    Animal = apps.get_model("animals", "Animal")
    Animal.objects.filter(profile_image="").update(profile_image=OLD_DEFAULT)


class Migration(migrations.Migration):
    dependencies = [
        ("animals", "0006_animal_date_of_death_animal_memorial_note"),
    ]

    operations = [
        migrations.AlterField(
            model_name="animal",
            name="profile_image",
            field=models.ImageField(blank=True, default="", upload_to="profile_pics/animals"),
        ),
        migrations.RunPython(blank_out_default_profile_image, restore_default_profile_image),
    ]
