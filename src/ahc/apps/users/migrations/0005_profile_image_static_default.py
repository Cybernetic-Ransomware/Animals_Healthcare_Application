from django.db import migrations, models

OLD_DEFAULT = "profile_pics/signup2.png"


def blank_out_default_profile_image(apps, schema_editor):
    Profile = apps.get_model("users", "Profile")
    Profile.objects.filter(profile_image=OLD_DEFAULT).update(profile_image="")


def restore_default_profile_image(apps, schema_editor):
    Profile = apps.get_model("users", "Profile")
    Profile.objects.filter(profile_image="").update(profile_image=OLD_DEFAULT)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0004_profile_discord_user_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="profile_image",
            field=models.ImageField(blank=True, default="", upload_to="profile_pics/users"),
        ),
        migrations.RunPython(blank_out_default_profile_image, restore_default_profile_image),
    ]
