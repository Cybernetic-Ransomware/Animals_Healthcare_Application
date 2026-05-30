from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("homepage", "0003_cronjob"),
    ]

    operations = [
        migrations.DeleteModel(name="CronJob"),
    ]
