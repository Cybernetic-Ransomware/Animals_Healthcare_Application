from django.db import models
from users.models import Profile as UserProfile


class BiometricRecord(models.Model):
    height = models.IntegerField(default=0)  # always in grams, set validation to int values (if float, ask if save as integer grams)
    height_date_updated = models.DateTimeField(auto_now_add=True, editable=True)

    weight = models.DecimalField(max_digits=6, decimal_places=2, default=0, null=True)
    weight_unit = models.CharField(max_length=5, default='mm', blank=False)
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

    owner = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True) # dodac okresową notyfikację o braku ownera - przypisuje admin z panelu
    allowed_users = models.ManyToManyField(UserProfile, null=True)

    # first_contact_vet = models.ForeignKey(Vet_pofile)
    # first_contact_medical_place = models.ForeignKey(Place_profile)

    last_control_visit = models.DateTimeField(null=True, blank=True)

    biometric_records = models.OneToOneField(BiometricRecord, on_delete=models.SET_NULL, null=True)


# biometric_records_history = # relacja jeden do jeden w notatce
# medical_records_history = None  # relacja jeden do jeden do notatki
# feeding_records_history = None # relacja jeden do jeden w notatce


class CurrentDiet(models.Model):
    animal = models.ForeignKey(Animal, on_delete=models.SET_NULL)
    start_date = None
    end_date = None
    food_type = None
    name = None
    producer = None
    description = None

    # wykorzystywana zarówno do jedzenia, jak i do medykamentów,
    # + sygnał przepisywania na notatkę (obsłuż haszowanie do edytowania id notatki i rodziel daty zakładane od rzeczywistych)
    # + możliwość kopiowania do innego zwierzęcia
    # później stworzyć apkę do kartoteki produktów, zbudować rejestrację i agregację kosztów


class CurrentMedicine(CurrentDiet):
    frequency_description = None

    notifications_is_active = None
    notification_form = None
    notification_message = None
    notification_frequency_interval = None

    # co jeszcze odroznia medykament od pokarmu?
    # dostępne inne produkty z kartoteki
    # zaplanować pod możliwość konwertowania datetime i ustawienia notyfikacji


class MedicalRecord(models.Model):
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE)

    date_creation = None
    date_updated = None
    date_event_started = None
    date_event_ended = None

    participants = None
    place = None

    short_description = None
    full_description = None

    type_of_event = None
    event_details = None
