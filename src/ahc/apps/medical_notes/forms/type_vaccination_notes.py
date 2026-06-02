from __future__ import annotations

from django import forms

from ahc.apps.medical_notes.models.type_vaccination_notes import VaccinationNote


class VaccinationNoteForm(forms.ModelForm):
    """Form for creating and editing a VaccinationNote.

    Used by the inline click-to-edit table rows on the Vaccinations tab.
    Date fields use the HTML5 date picker to match the rest of the app.
    """

    class Meta:
        model = VaccinationNote
        fields = [
            "vaccine_name",
            "last_vaccination_date",
            "valid_until",
            "suggested_clinic",
            "reminder_date",
        ]
        widgets = {
            "last_vaccination_date": forms.DateInput(attrs={"type": "date"}),
            "valid_until": forms.DateInput(attrs={"type": "date"}),
            "reminder_date": forms.DateInput(attrs={"type": "date"}),
        }
        labels = {
            "vaccine_name": "Vaccine name",
            "last_vaccination_date": "Last vaccinated",
            "valid_until": "Valid until",
            "suggested_clinic": "Suggested clinic",
            "reminder_date": "Remind me on",
        }
