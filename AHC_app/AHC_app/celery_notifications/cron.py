import logging
from datetime import datetime, time, timedelta
from functools import wraps

import pytz
from django.db.models import QuerySet
from django.urls import reverse
from medical_notes.models.type_feeding_notes import EmailNotification

from AHC_app.celery_notifications.config import send_email_notifications

logging.basicConfig(
    filename="logs/cron.log",
    force=True,
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def log_exceptions_and_notifications(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            notifications_to_send = func(*args, **kwargs)
            logger.debug(f"Notifications to send: {notifications_to_send}")
            return notifications_to_send

        except Exception as e:
            logger.exception(f"Failed to send notification {func.__name__}: {e}")

    return wrapper


def calculate_time_difference(daily_timestamp: time) -> int:
    current_time = datetime.now().time()

    current_datetime = datetime.combine(datetime.today(), current_time)
    daily_datetime = datetime.combine(datetime.today(), daily_timestamp)

    time_difference: int = int((daily_datetime - current_datetime).total_seconds())

    return max(time_difference, 0)


@log_exceptions_and_notifications
def get_notifications_to_send() -> QuerySet[EmailNotification]:
    local_timezone = pytz.timezone("GMT")
    current_time: datetime = datetime.now(tz=local_timezone)
    next_hour: datetime = current_time + timedelta(hours=1)

    current_time_time: time = current_time.time()
    next_hour_time: time = next_hour.time()

    notifications_to_send: QuerySet[
        EmailNotification
    ] = EmailNotification.objects.filter(
        related_note__start_date__lte=next_hour.date(),
        related_note__end_date__gte=current_time.date(),
        related_note__is_active=True,
        # related_note__days_of_week__contains=[current_weekday_number],
        related_note__daily_timestamp__time__gte=current_time_time,
        related_note__daily_timestamp__time__lt=next_hour_time,
    )

    return notifications_to_send


@log_exceptions_and_notifications
def send_emails() -> None:
    notifications_to_send = get_notifications_to_send()
    for notification in notifications_to_send:
        user_set_zone: str = notification.related_note.timezone
        user_weekday_number: int = datetime.now(
            tz=pytz.timezone(user_set_zone)
        ).weekday()

        if user_weekday_number in notification.related_note.days_of_week:
            break

        email: list[str] = list(notification.email)
        animal: str = notification.related_note.related_note.animal
        receiver_name: str = notification.related_note.receiver_name
        header: str = f"Hi, {receiver_name}"

        message: str = notification.related_note.message
        note_url: str = reverse(
            "note_edit", kwargs={"pk": notification.related_note.id}
        )
        center: str = f"{message} \n\n " f"For further information:\n{note_url}"

        sender: str = notification.related_note.related_note.author
        footer: str = f"Best regards \n{sender}"

        subject = f"Subscription for feeding plan of {animal}"
        content = f"{header}\n\n{center}\n\n{footer}"
        delay: int = calculate_time_difference(
            notification.related_note.daily_timestamp
        )

        send_email_notifications.apply_async(
            kwargs={"recipient_list": email, "subject": subject, "message": content},
            countdown=delay,
        )


@log_exceptions_and_notifications
def send_sms():
    pass


@log_exceptions_and_notifications
def send_discord_notes():
    pass
