from celery import Celery
from celery.utils.log import get_task_logger
from django.conf import settings

from AHC_app.celery_notifications.utils.sending_utils import (
    send_via_email,  # , send_via_sms, send_via_discord
)

logger = get_task_logger(__name__)
celery_obj = Celery(
    "my_celery", broker="redis://redis:6379/0", backend="redis://redis:6379/0"
)

celery_obj.conf.broker_connection_retry_on_startup = True


@celery_obj.task()
def send_email_notifications(**kwargs):
    recipient_list = kwargs.get('email')
    subject = kwargs.get('subject')
    message = kwargs.get('message')
    sender_email = settings.EMAIL_HOST_USER

    send_via_email(subject=subject, message=message, from_email=sender_email, recipient_list=recipient_list, fail_silently=True)


@celery_obj.task()
def send_sms_notifications(**kwargs):
    # send_via_sms(**kwargs)
    pass


@celery_obj.task()
def send_discord_notifications(**kwargs):
    # send_via_discord(**kwargs)
    pass
