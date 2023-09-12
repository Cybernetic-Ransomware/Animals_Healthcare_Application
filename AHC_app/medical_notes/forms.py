from django import forms
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.db.models import Q

from animals.models import Animal as AnimalProfile
from .models import MedicalRecord


class MedicalRecordForm(forms.ModelForm):  # or forms.Form
    class Meta:
        model = MedicalRecord
        fields = [
            'date_event_started',
            'date_event_ended',
            'participants',
            'place',
            'short_description',
            'full_description',
            'type_of_event',
        ]

        # TYPES_OF_EVENTS = (
        #     ('option1', 'Opcja 1'),
        #     ('option2', 'Opcja 2'),
        #     ('option3', 'Opcja 3'),
        # )

        widgets = {
            "date_event_started": forms.DateInput(attrs={"type": "date"}),
            "date_event_ended": forms.DateInput(attrs={"type": "date"}),
            "short_description": forms.Textarea(attrs={"rows": 3, "cols": 2}),
            "full_description": forms.Textarea(attrs={"rows": 12, "cols": 2}),
            # "full_description": forms.ChoiceField(choices=TYPES_OF_EVENTS)
            'type_of_event': forms.Select(attrs={'class': 'custom-select'})
        }
