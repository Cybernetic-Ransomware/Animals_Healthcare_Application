from django import forms
from .models import BiometricHeightRecords, BiometricWeightRecords, BiometricCustomRecords


class BiometricRecordForm(forms.Form):
    RECORD_CHOICES = [
        ('weight', 'BiometricWeightRecords'),
        ('height', 'BiometricHeightRecords'),
        ('custom', 'BiometricCustomRecords'),
    ]

    record_type = forms.ChoiceField(choices=RECORD_CHOICES)

    weight = forms.IntegerField(required=False)
    weight_unit_to_present = forms.CharField(max_length=3, required=False)

    height = forms.IntegerField(required=False)
    height_unit_to_present = forms.CharField(max_length=3, required=False)

    custom_name = forms.CharField(max_length=30, required=False)
    custom_value = forms.CharField(max_length=255, required=False)
    custom_unit = forms.CharField(max_length=12, required=False)
