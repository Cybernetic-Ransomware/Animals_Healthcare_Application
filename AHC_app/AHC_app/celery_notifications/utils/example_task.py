from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


@shared_task(bind=True)
def send_mail_fnc(self):
    subject = "test subject"
    message = "test message"
    email = "scorpos6@gmail.com"
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=False,
    )
    return "Done"
