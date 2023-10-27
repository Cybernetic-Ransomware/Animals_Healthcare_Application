from django.conf import settings
from django.core.mail import send_mail


def create_message(max_length: int = 2500) -> str:
    print('test')
    message = 'test message'
    if len(message) > max_length:
        message = message[:max_length-4]
        message = message + '...'
    return message


def send_via_email(**kwargs):
    print(**kwargs)
    text_message: str = create_message()

    send_mail(
        "Animal notification",
        text_message,
        settings.EMAIL_HOST_USER,
        ["Scorpos6@gmail.com"],
        fail_silently=True,
    )


def send_via_sms(**kwargs):
    pass


def send_via_discord(**kwargs):
    pass
