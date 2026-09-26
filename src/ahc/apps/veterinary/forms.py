from __future__ import annotations

from django import forms

from ahc.apps.veterinary.models import MedicalPlace, Vet

DETAILS_HELP_TEXT = "Visible to keepers who have Vet contact access to this owner's animals."


class VetForm(forms.ModelForm):
    class Meta:
        model = Vet
        fields = ["name", "phone", "email", "details"]
        help_texts = {"details": DETAILS_HELP_TEXT}

    def __init__(self, *args, owner=None, **kwargs):
        self.owner = owner
        super().__init__(*args, **kwargs)


class MedicalPlaceForm(forms.ModelForm):
    class Meta:
        model = MedicalPlace
        fields = ["name", "phone", "email", "address", "website", "details"]
        help_texts = {"details": DETAILS_HELP_TEXT}

    def __init__(self, *args, owner=None, **kwargs):
        self.owner = owner
        super().__init__(*args, **kwargs)
