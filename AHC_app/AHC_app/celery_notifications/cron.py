from config import send_notifications
from datetime import datetime, timedelta
from django.db.models import Q, F, ExpressionWrapper, DateTimeField
from django.urls import reverse
from django.utils import timezone

from medical_notes.models.type_feeding_notes import EmailNotification


def send_emails():
    current_time = datetime.now()
    next_hour = current_time + timedelta(hours=1)

    notifications_to_send = EmailNotification.objects.filter(
        Q(
            related_note__start_date__lte=next_hour,
            related_note__end_date__gte=current_time,
            related_note__is_active=True,
        ),
        related_note__start_date__lte=F('related_note__start_date') + ExpressionWrapper(
            (F('related_note__start_date') - F('related_note__start_date')) % F('related_note__frequency_interval'),
            output_field=DateTimeField()
        )
    )

    for notification in notifications_to_send:

        note_url = reverse('note_edit', kwargs={"pk": notification.related_note.id})

        # send_notifications.apply_async
        # Call the task with a delay, example:
        # arg1_value = 'some_value'
        # arg2_value = 42
        # delayed_task = my_task.apply_async(args=[arg1_value, arg2_value], countdown=60)

        # send_notifications.delay(notify_type="email",
        #                          email=notification.email,
        #                          message=notification.message,
        #                          receiver_name=notification.receiver_name,
        #                          related_note=note_url)
        pass


def send_sms():
    pass


def send_discord_notes():
    pass
