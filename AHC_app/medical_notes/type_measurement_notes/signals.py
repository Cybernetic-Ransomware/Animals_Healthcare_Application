from django.db.models import Q
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError

from .models import BiometricRecord
from medical_notes.models import MedicalRecord
from users.models import Profile as UserProfile


@receiver(pre_save, sender=BiometricRecord)
def validate_one_to_one_fields(sender, instance, **kwargs):
    if len({instance for instance in (instance.weight_biometric_record, instance.height_biometric_record, instance.custom_biometric_record) if instance is not None}) > 1:
        raise ValidationError('BiometricRecord can only have one of OneToOneFields assigned.')


@receiver(post_save, sender=BiometricRecord)
def clean_orphaned_metric_records(sender, instance, **kwargs):
    user_profile = UserProfile.objects.get(id=instance.related_note.author.id)
    medical_records = MedicalRecord.objects.filter(author=user_profile, type_of_event='biometric_record')

    for record in medical_records:
        if not record.biometricrecord_set.filter(
                Q(weight_biometric_record__isnull=False) |
                Q(height_biometric_record__isnull=False) |
                Q(custom_biometric_record__isnull=False)
        ).exists():
            record.delete()
