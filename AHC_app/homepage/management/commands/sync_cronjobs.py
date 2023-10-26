import subprocess

from datetime import datetime
from django.core.management.base import BaseCommand
from homepage.models import CronJob


class Command(BaseCommand):
    help = 'Sync cronjobs with the actual cron configuration'

    def handle(self, *args, **options):
        cronjob_info = subprocess.run(["crontab", "-l"], stdout=subprocess.PIPE, text=True).stdout.splitlines()

        CronJob.objects.all().delete()

        for job_info in cronjob_info:

            schedule, command = job_info.split(" /", 1)
            function_name = command.strip().split('.')[-1]
            cron_job = CronJob(schedule=schedule, command=command)

            cron_job.name = f"Cron Job: {function_name}"
            cron_job.last_execution = None
            cron_job.next_execution = None
            cron_job.save()
