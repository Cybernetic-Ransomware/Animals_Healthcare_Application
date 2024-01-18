from animals.models import Animal
from django.db import models
from medical_notes.models.type_basic_note import MedicalRecord


class BiometricHeightRecords(models.Model):
    height = models.DecimalField(default=0, max_digits=8, decimal_places=3)
    # always in grams, set validation to int values (if is float, ask if save as integer grams)
    height_unit_to_present = models.CharField(max_length=3, default="mm", blank=False)


class BiometricWeightRecords(models.Model):
    weight = models.DecimalField(default=0, max_digits=8, decimal_places=3)
    # always in mm, set validation to int values (if is float, ask if save as integer grams)
    weight_unit_to_present = models.CharField(max_length=3, default="g", blank=False)


class BiometricCustomRecords(models.Model):
    record_name = models.CharField(max_length=30, blank=False, null=False)
    record_value = models.CharField(max_length=255, blank=False, null=False)
    record_unit = models.CharField(max_length=12, blank=False, null=False)


class BiometricRecord(models.Model):
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE)
    related_note = models.ForeignKey(
        MedicalRecord, on_delete=models.SET_NULL, blank=True, null=True
    )
    date_updated = models.DateTimeField(auto_now_add=True, editable=True)

    weight_biometric_record = models.OneToOneField(
        BiometricWeightRecords, on_delete=models.CASCADE, blank=True, null=True
    )
    height_biometric_record = models.OneToOneField(
        BiometricHeightRecords, on_delete=models.CASCADE, blank=True, null=True
    )
    custom_biometric_record = models.OneToOneField(
        BiometricCustomRecords, on_delete=models.CASCADE, blank=True, null=True
    )
