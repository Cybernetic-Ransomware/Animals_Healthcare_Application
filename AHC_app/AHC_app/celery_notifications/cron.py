import pytz

from config import send_notifications
from datetime import datetime, time, timedelta
from django.db.models import QuerySet, DateTimeField
from django.urls import reverse

from medical_notes.models.type_feeding_notes import EmailNotification


def calculate_time_difference(daily_timestamp: time) -> int:
    current_time = datetime.now().time()

    current_datetime = datetime.combine(datetime.today(), current_time)
    daily_datetime = datetime.combine(datetime.today(), daily_timestamp)

    time_difference: int = int((daily_datetime - current_datetime).total_seconds())

    return max(time_difference, 0)


def send_emails() -> None:
    local_timezone = pytz.timezone('GMT')
    current_time: datetime = datetime.now(tz=local_timezone)
    next_hour: datetime = current_time + timedelta(hours=1)

    current_time_time: time = current_time.time()
    next_hour_time: time = next_hour.time()

    notifications_to_send: QuerySet[EmailNotification] = EmailNotification.objects.filter(
        related_note__start_date__lte=next_hour.date(),
        related_note__end_date__gte=current_time.date(),
        related_note__is_active=True,
        # related_note__days_of_week__contains=[current_weekday_number],
        related_note__daily_timestamp__time__gte=current_time_time,
        related_note__daily_timestamp__time__lt=next_hour_time
    )

    for notification in notifications_to_send:
        user_set_zone: str = notification.related_note.timezone
        user_weekday_number: int = datetime.now(tz=pytz.timezone(user_set_zone)).weekday()

        if user_weekday_number in notification.related_note.days_of_week:
            break

        email: str = notification.email
        receiver_name: str = notification.related_note.receiver_name
        message: str = notification.related_note.receiver_name
        note_url: str = reverse('note_edit', kwargs={"pk": notification.related_note.id})
        delay: int = calculate_time_difference(notification.related_note.daily_timestamp)

        send_notifications.apply_async(kwargs={'email': email,
                                               'receiver_name': receiver_name,
                                               'message': message,
                                               'note_url': note_url,
                                               'delay': delay},
                                       countdown=60)


def send_sms():
    pass


def send_discord_notes():
    pass
