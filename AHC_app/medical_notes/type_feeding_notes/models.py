from django.db import models
from medical_notes.models import MedicalRecord


class FeedingNote(models.Model):
    related_note = models.ForeignKey(
        MedicalRecord, on_delete=models.SET_NULL, blank=True, null=True
    )

    # planned  dates are from MedicalRecord
    real_start_date = models.DateField(null=True, blank=True)
    real_end_date = models.DateField(null=True, blank=True)

    is_medicine = models.BooleanField(default=False)

    type = models.CharField(max_length=50)
    product_name = models.CharField(max_length=80)
    producer = models.CharField(max_length=120)
    dose_annotations = models.CharField(max_length=250)

    # create a view for the current diet and historical notes
    # create an app for the product catalog, build a registration of products, a purchases history and aggregation of costs
    # create separate catalogs of basic fodder and medicines/supplements

    # na klase abstrakcyjną i dziedziczyć przez każdy rodzaj notyfikacji, sprawdź w ćwiczeniach


class FeedingNotification(models.Model):
    related_note = models.ForeignKey(
        FeedingNote, on_delete=models.SET_NULL, blank=True, null=True
    )
    description = models.CharField(max_length=250)

    is_active = models.BooleanField(default=False, null=False)
    form = models.CharField(max_length=50)

    reciever_name = models.CharField(max_length=30)
    message = models.CharField(max_length=2500)

    start_date = models.DateField(null=False, blank=False)
    end_date = models.DateField(null=True, blank=True)
    frequency_interval = models.DurationField(null=True, blank=True)


class EmailNotification(models.Model):
    related_note = models.ForeignKey(
        FeedingNotification, on_delete=models.SET_NULL, blank=True, null=True
    )
    email = models.EmailField()

    # append sms and at least one communicator (e.g. Discord)
