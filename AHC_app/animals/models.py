import uuid

from django.db import models
from users.models import Profile as UserProfile


class BiometricRecord(models.Model):
    height = models.IntegerField(
        default=0
    )  # always in grams, set validation to int values (if is float, ask if save as integer grams)
    height_unit_to_present = models.CharField(max_length=3, default="g", blank=False)
    height_date_updated = models.DateTimeField(auto_now_add=True, editable=True)

    weight = models.IntegerField(
        default=0
    )  # always in mm, set validation to int values (if is float, ask if save as integer grams)
    weight_unit_to_presen = models.CharField(max_length=3, default="mm", blank=False)
    weight_date_updated = models.DateTimeField(auto_now_add=True, editable=True)

    # + sygnał archiwizowania do danych wykreślnych


class BiometricCustomRecords(models.Model):
    biometric_record = models.ForeignKey(BiometricRecord, on_delete=models.CASCADE)
    creation_date = models.DateTimeField(auto_now_add=True, editable=False)
    record_name = models.CharField(max_length=30, blank=False, null=False)
    record_value = models.CharField(max_length=255, blank=False, null=False)


class Animal(models.Model):
    full_name = models.CharField(max_length=50)
    short_description = models.CharField(max_length=250, blank=True)
    long_description = models.CharField(max_length=2500, blank=True)

    birthdate = models.DateField(null=True, blank=True)
    profile_image = models.ImageField(
        default="profile_pics/pet-care.png", upload_to="profile_pics/animals"
    )
    creation_date = models.DateTimeField(auto_now_add=True, editable=False)

    owner = models.ForeignKey(
        UserProfile, on_delete=models.SET_NULL, null=True
    )  # dodac okresową notyfikację o braku ownera - przypisuje admin z panelu
    allowed_users = models.ManyToManyField(UserProfile, null=True)

    first_contact_vet = models.CharField(max_length=250, blank=True)
    # first_contact_vet = models.ForeignKey(Vet_pofile)
    first_contact_medical_place = models.CharField(max_length=250, blank=True)
    # first_contact_medical_place = models.ForeignKey(Place_profile)

    last_control_visit = models.DateTimeField(null=True, blank=True)

    biometric_records = models.OneToOneField(
        BiometricRecord, on_delete=models.SET_NULL, null=True
    )


# biometric_records_history = # relacja jeden do jeden w notatce
# medical_records_history = None  # relacja jeden do jeden do notatki
# feeding_records_history = None # relacja jeden do jeden w notatce


class CurrentDiet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    animal = models.ForeignKey(Animal, on_delete=models.SET_NULL)
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
    animal = models.ForeignKey(Animal, on_delete=models.SET_NULL)
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

    # co jeszcze odroznia medykament od pokarmu?
    # dostępne inne produkty z kartoteki
    # zaplanować pod możliwość konwertowania datetime i ustawienia notyfikacji


class MedicalRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE)

    date_creation = models.DateTimeField(auto_now_add=True, editable=False)
    date_updated = models.DateTimeField(auto_now=True, editable=True)
    date_event_started = models.DateField(null=True, blank=True)
    date_event_ended = models.DateField(null=True, blank=True)

    # to cahnge to a new app models
    participants = models.CharField(max_length=80)
    place = models.CharField(max_length=80)

    short_description = models.CharField(max_length=125)
    full_description = models.CharField(max_length=2500)

    type_of_event = models.CharField(max_length=50)
    # reference to a new table, if needed for some types of records
    event_details = None

    # to use for hashtags
    note_tags = None
