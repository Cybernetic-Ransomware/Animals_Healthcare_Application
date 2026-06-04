import json
import logging
import logging.config
import logging.handlers
import pathlib
from datetime import date, datetime, time, timedelta
from functools import wraps

from django.db.models import Q, QuerySet
from django.tasks import task
from django.utils import timezone

from ahc.apps.medical_notes.models.type_feeding_notes import EmailNotification
from celery_notifications.config import (
    send_discord_notifications,
    send_email_notifications,
)
from celery_notifications.utils.example_task import send_mail_fnc

logger = logging.getLogger("crons_logger")


def setup_logging():
    config_file = pathlib.Path(__file__).parent / "logger_config.json"
    with open(config_file) as file:
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
        _user_set_zone: str = notification.timezone

        email: str = notification.email
        animal: str = notification.related_note.related_note.animal
        receiver_name: str = notification.receiver_name
        header: str = f"Hi, {receiver_name}"

        message: str = notification.message
        # note_url: str = reverse(
        #     "note_edit", kwargs={"pk": notification.related_note.id}
        # )
        note_url: str = ""
        center: str = f"{message} \n\n For further information:\n{note_url}"

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
    # notifications_to_send = get_notifications_to_send()
    #
    # if not notifications_to_send:
    #     return None

    user_id: int = 422570242275934219
    # user_id: int = 530756049913905172
    user_message = "Test message"
    delay: int = 0

    send_discord_notifications.apply_async(kwargs={"user_id": user_id, "user_message": user_message}, countdown=delay)


@log_exceptions_and_notifications
def clean_orphaned_profile_images() -> None:
    """Delete animal profile images with no corresponding Animal row.

    Runs as a daily Celery Beat task. Replaces the former post_save / post_delete
    full directory-scan signals on Animal and Profile that ran O(N images) on every
    write. Now runs once per day at 03:00 UTC.
    """
    import os
    from pathlib import Path

    from django.conf import settings

    from ahc.apps.animals.models import Animal

    animals_media_dir = Path(settings.MEDIA_ROOT) / "profile_pics" / "animals"
    if not animals_media_dir.is_dir():
        return
    live = {str(p).split("/")[-1] for p in Animal.objects.exclude(profile_image="").values_list("profile_image", flat=True)}
    for image_name in os.listdir(animals_media_dir):
        if image_name not in live:
            (animals_media_dir / image_name).unlink(missing_ok=True)


@log_exceptions_and_notifications
def send_vaccination_reminders() -> None:
    """Send Discord reminders for vaccinations whose reminder_date is today or overdue.

    Marks each record as reminder_sent=True after queuing so that the same
    reminder is not dispatched again on the next daily run.

    Animals whose owners have no discord_user_id are silently skipped
    (a warning is logged).  Actual Discord delivery remains stubbed until
    DISCORD_TOKEN is configured in the environment.
    """
    from datetime import date

    from ahc.apps.medical_notes.selectors import due_vaccination_reminders

    today = date.today()
    due = due_vaccination_reminders(today)

    for vaccination in due:
        animal = vaccination.related_note.animal
        owner = animal.owner

        if not owner or not owner.discord_user_id:
            logger.warning(
                "Vaccination reminder skipped — owner has no discord_user_id (animal=%s, vaccine=%s)",
                animal.id,
                vaccination.vaccine_name,
            )
            continue

        valid_str = vaccination.valid_until.strftime("%Y-%m-%d") if vaccination.valid_until else "unknown"
        user_message = (
            f"Vaccination reminder: {animal.full_name} is due for '{vaccination.vaccine_name}' (valid until {valid_str})."
        )

        send_discord_notifications.apply_async(
            kwargs={"user_id": int(owner.discord_user_id), "user_message": user_message},
            countdown=0,
        )

        vaccination.reminder_sent = True
        vaccination.save(update_fields=["reminder_sent"])


@task
def log_notification_count() -> int:
    """Django Background Tasks example. Use for simple in-process tasks.

    For distributed / retryable work, use Celery (@shared_task).
    Enqueue with: log_notification_count.enqueue()
    """
    count = EmailNotification.objects.filter(is_active=True).count()
    logger.info("Active email notifications: %d", count)
    return count
