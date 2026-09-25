from typing import cast

from django import forms
from django.db.models import Field

from ahc.apps.medical_notes.models.type_measurement_notes import BiometricHeightRecords, BiometricWeightRecords


class BiometricRecordForm(forms.Form):
    RECORD_CHOICES = [
        ("weight", "Weight Record"),
        ("height", "Height Record"),
        ("custom", "Custom Record"),
    ]

    record_type = forms.ChoiceField(choices=RECORD_CHOICES)

    weight = forms.DecimalField(max_digits=8, decimal_places=3, required=False)
    weight_unit_to_present = forms.CharField(max_length=3, required=False)

    height = forms.DecimalField(max_digits=8, decimal_places=3, required=False)
    height_unit_to_present = forms.CharField(max_length=3, required=False)

    custom_name = forms.CharField(max_length=30, required=False)
    custom_value = forms.CharField(max_length=255, required=False)
    custom_unit = forms.CharField(max_length=12, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        default_height_unit_to_present = cast(
            Field, BiometricHeightRecords._meta.get_field("height_unit_to_present")
        ).get_default()
        default_weight_unit_to_present = cast(
            Field, BiometricWeightRecords._meta.get_field("weight_unit_to_present")
        ).get_default()

        self.fields["height_unit_to_present"].initial = default_height_unit_to_present
        self.fields["weight_unit_to_present"].initial = default_weight_unit_to_present

    def clean(self):
        cleaned = super().clean() or {}
        record_type = cleaned.get("record_type")

        if record_type == "weight" and cleaned.get("weight") is None:
            self.add_error("weight", "Weight is required for a weight record.")
        elif record_type == "height" and cleaned.get("height") is None:
            self.add_error("height", "Height is required for a height record.")
        elif record_type == "custom":
            if not cleaned.get("custom_name"):
                self.add_error("custom_name", "Measurement name is required for custom records.")
            if not cleaned.get("custom_value"):
                self.add_error("custom_value", "Measurement value is required for custom records.")
            if not cleaned.get("custom_unit"):
                self.add_error("custom_unit", "Unit is required for custom records.")

        return cleaned
