from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from .models import BiometricRecord, BiometricHeightRecords, BiometricWeightRecords, BiometricCustomRecords


@receiver(pre_save, sender=BiometricRecord)
def validate_one_to_one_fields(sender, instance, **kwargs):
    if len({instance for instance in (instance.weight_biometric_record, instance.height_biometric_record, instance.custom_biometric_record) if instance is not None}) > 1:
        raise ValidationError('BiometricRecord can only have one OneToOneField assigned.')


# @receiver(post_save, sender=BiometricHeightRecords)
# def validate_one_to_one_fields(sender, instance, **kwargs):
#     if len({instance for instance in (instance.weight_biometric_record, instance.height_biometric_record, instance.custom_biometric_record) if instance is not None}) > 1:
#         raise ValidationError('BiometricRecord can only have one OneToOneField assigned.')
