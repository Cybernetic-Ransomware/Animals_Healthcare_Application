from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.contrib.postgres.fields import ArrayField
from django.db import models
from timezone_field import TimeZoneField

from medical_notes.models.type_basic_note import MedicalRecord


class FeedingNote(models.Model):
    related_note = models.ForeignKey(
        MedicalRecord, on_delete=models.CASCADE, null=False, blank=False
    )

    # planned  dates are from MedicalRecord
    real_start_date = models.DateField(null=True, blank=False)
    real_end_date = models.DateField(null=True, blank=False)

    is_medicine = models.BooleanField(default=False, null=False, blank=True)

    # to create app with products catalog
    category = models.CharField(max_length=50, null=False, blank=False)
    product_name = models.CharField(max_length=80)
    producer = models.CharField(max_length=120)
    dose_annotations = models.CharField(max_length=250)

    # create a view for the current diet and historical notes
    # create an app for the product catalog, build a registration of products, a purchases history and aggregation of costs
    # create separate catalogs of basic fodder and medicines/supplements


class NotificationRecordManager(models.Manager):
    @staticmethod
    def convert_to_utc(local_time, user_timezone):

        local_datetime = datetime.combine(date.today(), local_time)

        local_datetime_with_tz = local_datetime.replace(tzinfo=user_timezone)
        utc_datetime = local_datetime_with_tz.astimezone(ZoneInfo("UTC"))

        return utc_datetime.time()

    def create_notification(self, daily_timestamp, timezone, **kwargs):
        utc_time = self.convert_to_utc(daily_timestamp, timezone)

        return self.create(timezone=timezone, daily_timestamp=utc_time, **kwargs)


class FeedingNotification(models.Model):
    related_note = models.ForeignKey(
        FeedingNote, on_delete=models.CASCADE, blank=True, null=True
    )
    description = models.CharField(max_length=250)

    is_active = models.BooleanField(default=False, null=False)

    receiver_name = models.CharField(max_length=30)
    message = models.CharField(max_length=2500)

    start_date = models.DateField(null=False, blank=False)
    end_date = models.DateField(null=True, blank=True)
    timezone = TimeZoneField(default="Europe/London")

    # keep in a database timezone, to verify save and show as a local time
    daily_timestamp = models.TimeField(null=True, blank=True)

    # 0 -> Monday, 6 -> Sunday
    days_of_week = ArrayField(
        ArrayField(models.BooleanField(default=False, blank=True), size=1),
        size=7,
    )

    objects = NotificationRecordManager()

    class Meta:
        abstract = True


class EmailNotification(FeedingNotification):
    email = models.EmailField()


class SMSNotification(FeedingNotification):
    number = models.PositiveIntegerField(null=False, blank=False)
    country_code = models.CharField(max_length=5, default="+48", null=False, blank=True)

    message = models.CharField(max_length=160)


class DiscordNotification(FeedingNotification):
    user_id = models.PositiveBigIntegerField(null=False, blank=False)
    bot_id = models.PositiveBigIntegerField(null=False, blank=False)
