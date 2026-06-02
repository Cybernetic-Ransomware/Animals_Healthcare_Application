import os

from celery import Celery, shared_task
from celery.schedules import crontab
from celery.utils.log import get_task_logger
from django.conf import settings

# from celery_notifications.utils.discord_utils import send_via_discord
from celery_notifications.utils.sending_utils import send_via_email

logger = get_task_logger(__name__)


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ahc.settings")
celery_obj = Celery("ahc")

celery_obj.config_from_object("django.conf:settings", namespace="CELERY")
celery_obj.conf.broker_connection_retry_on_startup = True
celery_obj.autodiscover_tasks()


@celery_obj.task(name="ahc.beat.dispatch_discord_notes")
def dispatch_discord_notes():
    from celery_notifications.cron import send_discord_notes

    send_discord_notes()


@celery_obj.task(name="ahc.beat.dispatch_vaccination_reminders")
def dispatch_vaccination_reminders():
    from celery_notifications.cron import send_vaccination_reminders

    send_vaccination_reminders()


celery_obj.conf.beat_schedule = {
    "send-discord-notes-hourly": {
        "task": "ahc.beat.dispatch_discord_notes",
        "schedule": crontab(minute=6),
    },
    "send-vaccination-reminders-daily": {
        "task": "ahc.beat.dispatch_vaccination_reminders",
        "schedule": crontab(hour=8, minute=0),
    },
}


@celery_obj.task()
def send_email_notifications(*args, **kwargs):
    recipient_list = kwargs.get("email")
    subject = kwargs.get("subject")
    message = kwargs.get("message")
    sender_email = settings.EMAIL_HOST_USER

    send_via_email(
        subject=subject,
        message=message,
        from_email=sender_email,
        recipient_list=recipient_list,
        fail_silently=True,
    )


@shared_task(bind=True)
def send_sms_notifications(**kwargs):
    # send_via_sms(**kwargs)
    pass


@shared_task(bind=True)
def send_discord_notifications(self, *args, **kwargs):
    # user_id = kwargs.get("user_id")
    # user_message = kwargs.get("user_message")
    # send_via_discord(user_id, user_message)
    pass
