from django import forms
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.db.models import Q

from animals.models import Animal as AnimalProfile
from .models import MedicalRecord


class MedicalRecordForm(forms.ModelForm):
    class Meta:
        model = MedicalRecord
        fields = [
            'type_of_event',
            'participants',
            'place',
            'short_description',
            'full_description',
            'date_event_started',
            'date_event_ended',
            'note_tags'
        ]

        TYPES_OF_EVENTS = (
            ('fast_note',         'Fast note'),
            ('medical_visit',     'Medical visit'),
            ('biometric_record',  'Biometric record'),
            ('diet_note',         'Diet note'),
            ('medicament_note',   'Medicament note'),
            ('other_user_note',   'Other'),
        )

        widgets = {
            "date_event_started": forms.DateInput(attrs={"type": "date", "required": False}),
            "date_event_ended": forms.DateInput(attrs={"type": "date", "required": False}),
            "short_description": forms.Textarea(attrs={"rows": 3, "cols": 2}),
            "full_description": forms.Textarea(attrs={"rows": 12, "cols": 2, "required": False}),
            "type_of_event": forms.Select(choices=TYPES_OF_EVENTS, attrs={'class': 'custom-select'}),
            "participants": forms.TextInput(attrs={"required": False}),
            "place": forms.TextInput(attrs={"required": False}),
            "note_tags": forms.TextInput(attrs={"required": False})
        }

    def __init__(self, *args, **kwargs):
        super(MedicalRecordForm, self).__init__(*args, **kwargs)
        self.initial['type_of_event'] = 'fast_note'
