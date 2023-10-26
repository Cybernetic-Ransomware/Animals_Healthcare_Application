from django.core.mail import send_mail


def create_message(max_length: int = 2500) -> str:
    print('test')
    message = 'test message'
    if len(message) > max_length:
        message = message[:max_length-4]
        message = message + '...'
    return message


def send_emails(*args):
    print(*args)
    text_message: str = create_message()

    send_mail(
        "Animal notification",
        text_message,
        "from@example.com",
        ["Scorpos6@gmail.com"],
        fail_silently=True,
    )


def send_sms():
    create_message()


def send_discord_notes():
    create_message()
