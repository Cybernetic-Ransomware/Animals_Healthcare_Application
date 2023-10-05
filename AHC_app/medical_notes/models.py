import uuid

from django.db import models
from taggit.managers import TaggableManager
from taggit.models import GenericUUIDTaggedItemBase, TaggedItemBase

from animals.models import Animal
from users.models import Profile as UserProfile


class UUIDTaggedItem(GenericUUIDTaggedItemBase, TaggedItemBase):
    class Meta:
        verbose_name = ("Tag")
        verbose_name_plural = ("Tags")


class MedicalRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE)
    additional_animals = models.ManyToManyField(Animal, related_name='additional_animals', blank=True)
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


class BiometricHeightRecords(models.Model):
    height = models.IntegerField(default=0)
    # always in grams, set validation to int values (if is float, ask if save as integer grams)
    height_unit_to_present = models.CharField(max_length=3, default="g", blank=False)


class BiometricWeightRecords(models.Model):
    weight = models.IntegerField(default=0)
    # always in mm, set validation to int values (if is float, ask if save as integer grams)
    weight_unit_to_present = models.CharField(max_length=3, default="mm", blank=False)


class BiometricCustomRecords(models.Model):
    record_name = models.CharField(max_length=30, blank=False, null=False)
    record_value = models.CharField(max_length=255, blank=False, null=False)
    record_unit = models.CharField(max_length=12, blank=False, null=False)


class BiometricRecord(models.Model):
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE)
    related_note = models.ForeignKey(MedicalRecord, on_delete=models.SET_NULL, blank=True, null=True)
    date_updated = models.DateTimeField(auto_now_add=True, editable=True)

    weight_biometric_record = models.OneToOneField(BiometricHeightRecords, on_delete=models.CASCADE, blank=True, null=True)
    height_biometric_record = models.OneToOneField(BiometricWeightRecords, on_delete=models.CASCADE, blank=True, null=True)
    custom_biometric_record = models.OneToOneField(BiometricCustomRecords, on_delete=models.CASCADE, blank=True, null=True)


class CurrentDiet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    food_type = models.CharField(max_length=50)
    name = models.CharField(max_length=80)
    producer = models.CharField(max_length=120)
    description = models.CharField(max_length=250)

    # + sygnał przepisywania na notatkę (obsłuż haszowanie do edytowania id notatki i rodziel daty zakładane od rzeczywistych)
    # + możliwość kopiowania do innego zwierzęcia
    # później stworzyć apkę do kartoteki produktów, zbudować rejestrację i agregację kosztów


class CurrentMedicine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    food_type = models.CharField(max_length=50)
    name = models.CharField(max_length=80)
    producer = models.CharField(max_length=120)
    description = models.CharField(max_length=250)

    frequency_description = models.CharField(max_length=250)

    notifications_is_active = models.BooleanField(default=False, null=False)
    notification_form = models.CharField(max_length=50)
    notification_message = models.CharField(max_length=2500)
    notification_frequency_interval = models.DurationField(null=True, blank=True)

    # co odroznia medykament od pokarmu?
    # dostępne inne produkty z kartoteki
    # zaplanować pod możliwość konwertowania datetime i ustawienia notyfikacji
