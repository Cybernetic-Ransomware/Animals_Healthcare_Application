from django.conf import settings
from django.core.mail import send_mail


def standardize_message_size(message: str, max_length: int = 2500) -> str:
    if len(message) > max_length:
        message = message[:max_length-4]
        message = message + '...'
    return message


def send_via_email(**kwargs):
    recipient_list = kwargs.get('email')
    subject = kwargs.get('subject')
    message = kwargs.get('message')
    message = standardize_message_size(message, max_length=2500)
    sender_email = settings.EMAIL_HOST_USER

    send_mail(subject=subject, message=message, from_email=sender_email, recipient_list=recipient_list, fail_silently=True)


def send_via_sms(**kwargs):
    pass


def send_via_discord(**kwargs):
    pass
