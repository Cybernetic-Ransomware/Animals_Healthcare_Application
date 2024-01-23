import json
import logging
import logging.config
import logging.handlers
import pathlib
from datetime import date, datetime, time, timedelta
from functools import wraps

from django.db.models import Q, QuerySet
from django.utils import timezone
from django_cron import CronJobBase, Schedule
from medical_notes.models.type_feeding_notes import EmailNotification

from AHC_app.celery_notifications.config import send_email_notifications
from AHC_app.celery_notifications.utils.example_task import send_mail_fnc

logger = logging.getLogger("crons_logger")


def setup_logging():
    config_file = pathlib.Path("AHC_app/celery_notifications/logger_config.json")
    with open(config_file, "r") as file:
        config = json.load(file)
    logging.config.dictConfig(config)


def log_exceptions_and_notifications(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            setup_logging()
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
    current_time: datetime = timezone.now()

    current_time_time: time = current_time.time()
    current_date: date = current_time.date()
    current_week_number: int = current_time.isocalendar()[1]

    next_hour: datetime = current_time + timedelta(hours=1)
    next_hour_time: time = next_hour.time()

    notifications_to_send = EmailNotification.objects.filter(
        Q(end_date__gt=current_date) | Q(end_date=None),
        start_date__lt=current_date,
        is_active=True,
        days_of_week__contains=[current_week_number],
        # timestamp was saved as in UTC+0 timezone
        daily_timestamp__gt=current_time_time,
        daily_timestamp__lt=next_hour_time,
    )

    return notifications_to_send


@log_exceptions_and_notifications
def send_emails() -> None:
    notifications_to_send = get_notifications_to_send()

    if not notifications_to_send:
        return None

    for notification in notifications_to_send:
        user_set_zone: str = notification.timezone
        # user_weekday_number: int = datetime.now(
        #     tz=pytz.timezone(user_set_zone)
        # ).weekday()
        #
        # if user_weekday_number in notification.related_note.days_of_week:
        #     break

        email: str = notification.email
        animal: str = notification.related_note.related_note.animal
        receiver_name: str = notification.receiver_name
        header: str = f"Hi, {receiver_name}"

        message: str = notification.message
        # note_url: str = reverse(
        #     "note_edit", kwargs={"pk": notification.related_note.id}
        # )
        note_url: str = ""
        center: str = f"{message} \n\n " f"For further information:\n{note_url}"

        sender: str = notification.related_note.related_note.author
        footer: str = f"Best regards \n{sender}"

        subject = f"Subscription for feeding plan of {animal}"
        content = f"{header}\n\n{center}\n\n{footer}"
        # delay: int = calculate_time_difference(
        #     notification.daily_timestamp
        # )

        delay: int = 0

        send_email_notifications.apply_async(
            kwargs={"recipient_list": email, "subject": subject, "message": content},
            countdown=delay,
        )


@log_exceptions_and_notifications
def send_email_example() -> None:
    from icecream import ic

    ic()
    send_mail_fnc.delay()
    ic()

    return None


@log_exceptions_and_notifications
def send_sms():
    pass


@log_exceptions_and_notifications
def send_discord_notes():
    pass


class SynchNotificationsCron(CronJobBase):
    RUN_EVERY_MINS = 60

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = "AHC_app.SynchNotificationsCronJob"

    run_at_times = ["55"]

    @staticmethod
    def cron_send_emails():
        from icecream import ic

        ic()

        send_emails()
