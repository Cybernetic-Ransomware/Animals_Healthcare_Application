from django import forms

# from animals.models import Animal as AnimalProfile
from .models import MedicalRecord

# from django.core.validators import MaxLengthValidator, MinLengthValidator
# from django.db.models import Q


class MedicalRecordForm(forms.ModelForm):
    class Meta:
        model = MedicalRecord
        fields = [
            "type_of_event",
            "participants",
            "place",
            "short_description",
            "full_description",
            "date_event_started",
            "date_event_ended",
            "note_tags",
            "additional_animals",
        ]

        TYPES_OF_EVENTS = (
            ("fast_note", "Fast note"),
            ("medical_visit", "Medical visit"),
            ("biometric_record", "Biometric record"),
            ("diet_note", "Diet note"),
            ("medicament_note", "Medicament note"),
            ("other_user_note", "Other"),
        )

        widgets = {
            "date_event_started": forms.DateInput(
                attrs={"type": "date", "required": False}
            ),
            "date_event_ended": forms.DateInput(
                attrs={"type": "date", "required": False}
            ),
            "short_description": forms.Textarea(attrs={"rows": 3, "cols": 2}),
            "full_description": forms.Textarea(
                attrs={"rows": 12, "cols": 2, "required": False}
            ),
            "type_of_event": forms.Select(
                choices=TYPES_OF_EVENTS, attrs={"class": "custom-select"}
            ),
            "participants": forms.TextInput(attrs={"required": False}),
            "place": forms.TextInput(attrs={"required": False}),
            "note_tags": forms.TextInput(attrs={"required": False}),
            "additional_animals": forms.SelectMultiple(attrs={"required": False}),
        }

    def __init__(self, *args, **kwargs):
        animal_choices = kwargs.pop("animal_choices", None)
        type_of_event_param = kwargs.pop("type_of_event_param", None)
        super(MedicalRecordForm, self).__init__(*args, **kwargs)

        if animal_choices:
            self.fields["additional_animals"].widget.choices = animal_choices

        type_of_event = {"fast_note", "medical_visit", "biometric_record", "diet_note", "medicament_note", "other_user_note"}
        if type_of_event_param in set(event[0] for event in type_of_event):
            self.fields["type_of_event"].initial = type_of_event_param
        else:
            self.fields["type_of_event"].initial = "fast_note"

        self.fields["additional_animals"].label = "Related animals"


class MedicalRecordEditForm(MedicalRecordForm):
    def __init__(self, *args, **kwargs):
        animal = kwargs.pop('animal', None)
        super(MedicalRecordEditForm, self).__init__(*args, **kwargs)
        self.animal = animal
        tag_names = list(self.instance.note_tags.values_list("name", flat=True))
        self.initial["note_tags"] = ", ".join(tag_names)

        self.initial["type_of_event"] = self.instance.type_of_event
        self.fields["type_of_event"].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        print(cleaned_data)
        additional_animals = cleaned_data.get("additional_animals")
        print(f'{self.animal=}')
        print(f'{additional_animals=}')

        if self.animal in additional_animals:
            raise forms.ValidationError("The main Animal cannot be selected as an additional animal.")

        return cleaned_data


class MedicalRecordEditRelatedAnimalsForm(forms.ModelForm):
    class Meta:
        model = MedicalRecord
        fields = ["animal", "additional_animals"]

    def __init__(self, *args, **kwargs):

        animal_choices = kwargs.pop("animal_choices", None)
        is_author = kwargs.pop("is_author", None)
        super(MedicalRecordEditRelatedAnimalsForm, self).__init__(*args, **kwargs)

        if animal_choices:
            self.fields["animal"].widget.choices = animal_choices
            self.fields["additional_animals"].widget.choices = animal_choices

        if not is_author:
            del self.fields["animal"]

    def clean(self):
        cleaned_data = super().clean()
        print(cleaned_data)
        animal = cleaned_data.get("animal")
        additional_animals = cleaned_data.get("additional_animals")

        if animal in additional_animals:
            raise forms.ValidationError("The main Animal cannot be selected as an additional animal.")

        return cleaned_data
