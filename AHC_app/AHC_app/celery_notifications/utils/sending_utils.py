from django.conf import settings


def standardize_message_size(message: str, max_length: int = 2500) -> str:
    if len(message) > max_length:
        message = message[: max_length - 4]
        message = message + "..."
    return message


def send_via_email(**kwargs):
    recipient_list = kwargs.get("email")
    subject = kwargs.get("subject")
    message = kwargs.get("message")
    message = standardize_message_size(message, max_length=2500)
    sender_email = settings.EMAIL_HOST_USER

    print("DUPA", settings.EMAIL_HOST, settings.EMAIL_PORT, sender_email, flush=True)

    import smtplib

    sender = "Private Person <from@example.com>"
    receiver = "A Test User <to@example.com>"

    message = f"""\
    Subject: Hi Mailtrap
    To: {receiver}
    From: {sender}

    This is a test e-mail message."""

    with smtplib.SMTP("sandbox.smtp.mailtrap.io", 2525) as server:
        server.login("0c425676241dc7", "3ca81a9102980f")
        server.sendmail(sender, receiver, message)

    # send_mail(subject=subject, message=message, from_email=sender_email, recipient_list=recipient_list, fail_silently=False)


def send_via_sms(**kwargs):
    pass


def send_via_discord(**kwargs):
    pass
