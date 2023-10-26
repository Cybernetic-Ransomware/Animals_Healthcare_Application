from celery import Celery
from celery.utils.log import get_task_logger

from utils import send_via_email, send_via_sms, send_via_discord


logger = get_task_logger(__name__)
celery_obj = Celery(
    "my_celery", broker="redis://redis:6379/0", backend="redis://redis:6379/0"
)


@celery_obj.task()
def send_notifications(notify_type, **kwargs):
    match notify_type:
        case "email":
            send_via_email(**kwargs)
        case "sms":
            send_via_sms(**kwargs)
        case "chatbot":
            send_via_discord(**kwargs)
        case _:
            raise ValueError("Unexpected type of notification")
