import uuid

from django.db import models
from animals.models import Animal


class MedicalRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE)

    date_creation = models.DateTimeField(auto_now_add=True, editable=False)
    date_updated = models.DateTimeField(auto_now=True, editable=True)
    date_event_started = models.DateField(null=True, blank=True)
    date_event_ended = models.DateField(null=True, blank=True)

    # to change to a new app models
    participants = models.CharField(max_length=80, blank=True)
    place = models.CharField(max_length=80, blank=True)

    short_description = models.CharField(max_length=125)
    full_description = models.CharField(max_length=2500, blank=True)

    type_of_event = models.CharField(max_length=50)

    # reference to a new table, if needed for some types of records
    event_details = None

    # to use for hashtags
    note_tags = None
