"""Forms for the batch biometric measurement entry screen."""

from __future__ import annotations

from django import forms
from django.forms import formset_factory

from ahc.apps.medical_notes.forms.type_measurement_notes import BiometricRecordForm


class BiometricBatchSessionForm(forms.Form):
    """Controls the measurement type and unit for an entire batch session.

    A single session covers one record_type (weight / height / custom) applied
    to all animals on the screen. The optional `unit` field overrides the model
    default for weight ("g") and height ("mm"). Custom measurements require both
    `custom_name` and `custom_unit`.
    """

    record_type = forms.ChoiceField(choices=BiometricRecordForm.RECORD_CHOICES, label="Measurement type")
    unit = forms.CharField(
        max_length=12,
        required=False,
        label="Unit",
        help_text="Leave blank to use the model default (g for weight, mm for height).",
    )
    custom_name = forms.CharField(
        max_length=30,
        required=False,
        label="Measurement name",
        help_text="Required when record type is Custom.",
    )
    custom_unit = forms.CharField(
        max_length=12,
        required=False,
        label="Custom unit",
        help_text="Required when record type is Custom.",
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("record_type") == "custom":
            if not cleaned.get("custom_name"):
                self.add_error("custom_name", "Measurement name is required for custom records.")
            if not cleaned.get("custom_unit"):
                self.add_error("custom_unit", "Custom unit is required for custom records.")
        return cleaned


class BiometricBatchRowForm(forms.Form):
    """A single animal row in the batch measurement table.

    The `animal_id` hidden field carries the animal UUID from GET to POST so the
    view can look it up in the allowed set without trusting URL order. When
    `include` is True, `value` must be provided.
    """

    include = forms.BooleanField(required=False, label="Include")
    animal_id = forms.UUIDField(widget=forms.HiddenInput)
    value = forms.DecimalField(
        max_digits=8,
        decimal_places=3,
        required=False,
        label="Value",
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("include") and cleaned.get("value") is None:
            self.add_error("value", "A value is required for checked animals.")
        return cleaned


BiometricBatchFormSet = formset_factory(BiometricBatchRowForm, extra=0)
