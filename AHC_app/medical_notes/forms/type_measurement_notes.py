from django import forms

from medical_notes.models.type_measurement_notes import BiometricHeightRecords, BiometricWeightRecords


class BiometricRecordForm(forms.Form):
    RECORD_CHOICES = [
        ("weight", "Weight Record"),
        ("height", "Height Record"),
        ("custom", "Custom Record"),
    ]

    record_type = forms.ChoiceField(choices=RECORD_CHOICES)

    weight = forms.IntegerField(required=False)
    weight_unit_to_present = forms.CharField(max_length=3, required=False)

    height = forms.IntegerField(required=False)
    height_unit_to_present = forms.CharField(max_length=3, required=False)

    custom_name = forms.CharField(max_length=30, required=False)
    custom_value = forms.CharField(max_length=255, required=False)
    custom_unit = forms.CharField(max_length=12, required=False)

    def __init__(self, *args, **kwargs):
        super(BiometricRecordForm, self).__init__(*args, **kwargs)

        default_height_unit_to_present = BiometricHeightRecords._meta.get_field(
            "height_unit_to_present"
        ).get_default()
        default_weight_unit_to_present = BiometricWeightRecords._meta.get_field(
            "weight_unit_to_present"
        ).get_default()

        self.fields["height_unit_to_present"].initial = default_height_unit_to_present
        self.fields["weight_unit_to_present"].initial = default_weight_unit_to_present
