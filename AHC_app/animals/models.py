from django.db import models


class BiometricCustomRecords(models.Model):
    biometric_record = None
    record_name = None
    record_value = None


class BiometricRecord(models.Model):
    animal = None
    height = None
    weight = None


class MedicalRecord(models.Model):
    animal = None

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


class Animal(models.Model):
    full_name = None
    short_description = None
    long_description = None

    birthdate = None
    profile_image = None
    creation_date = None

    allowed_keepers = None  # TO_DO przeniesc do Usera (do many to one)
    first_contact_vet = None
    first_contact_medical_place = None

    # biometric_records = None
    # biometric_records_history = None

    last_control_visit = None
    medical_records = None

    feeding_records = None
    current_diet = None
    current_medications = None
