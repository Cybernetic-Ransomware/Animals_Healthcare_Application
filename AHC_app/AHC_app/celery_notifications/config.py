import os

from celery import Celery, shared_task
from celery.utils.log import get_task_logger
from django.conf import settings

from AHC_app.celery_notifications.utils.discord_utils import send_via_discord
from AHC_app.celery_notifications.utils.sending_utils import (
    send_via_email,  # , send_via_sms, send_via_discord
)

logger = get_task_logger(__name__)


os.environ.setdefault("DJANGO_SETTING_MODULE", "django_with_celery.settings")
celery_obj = Celery("django_with_celery")

celery_obj.config_from_object("django.conf:settings", namespace="CELERY")
celery_obj.conf.broker_connection_retry_on_startup = True
celery_obj.autodiscover_tasks(["AHC_app"])


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
    user_id = kwargs.get("user_id")
    user_message = kwargs.get("user_message")
    send_via_discord(user_id, user_message)
