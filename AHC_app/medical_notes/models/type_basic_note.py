import uuid

from animals.models import Animal
from django.db import models
from taggit.managers import TaggableManager
from taggit.models import GenericUUIDTaggedItemBase, TaggedItemBase
from users.models import Profile as UserProfile


class UUIDTaggedItem(GenericUUIDTaggedItemBase, TaggedItemBase):
    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"


class MedicalRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE)
    additional_animals = models.ManyToManyField(Animal, related_name="additional_animals", blank=True)
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE, null=True, blank=True)

    date_creation = models.DateTimeField(auto_now_add=True, editable=False)
    date_updated = models.DateTimeField(auto_now=True, editable=True)
    date_event_started = models.DateField(null=True, blank=True)
    date_event_ended = models.DateField(null=True, blank=True)

    participants = models.CharField(max_length=80, blank=True)
    place = models.CharField(max_length=80, blank=True)

    short_description = models.CharField(max_length=125)
    full_description = models.CharField(max_length=2500, blank=True)

    type_of_event = models.CharField(max_length=50)

    # reference to a new table, if needed for some types of records
    event_details = None

    note_tags = TaggableManager(through=UUIDTaggedItem, blank=True)


class MedicalRecordAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="static/media/attachments/")
    # url = models.CharField(max_length=255, blank=True)
    # description = models.CharField(max_length=255, blank=True)
    upload_date = models.DateTimeField(auto_now_add=True, editable=False)
