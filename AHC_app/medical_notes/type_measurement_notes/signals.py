from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from .models import BiometricRecord


@receiver(pre_save, sender=BiometricRecord)
def validate_one_to_one_fields(sender, instance, **kwargs):
    if len((instance.weight_biometric_record, instance.height_biometric_record, instance.custom_biometric_record)) > 1:
        raise ValidationError('BiometricRecord can only have one OneToOneField assigned.')
