from django import forms
from django.forms import ModelForm

from medical_notes.models.type_feeding_notes import FeedingNote


class DietRecordForm(forms.ModelForm):
    class Meta:
        model = FeedingNote
        fields = [
            "real_start_date",
            "real_end_date",
            "category",
            "producer",
            "product_name",
            "dose_annotations"
        ]
        labels = {
            "real_start_date": "Actual start date of feeding",
            "real_end_date": "Actual end date of feeding",
            "category": "Category",
            "producer": "Producer",
            "product_name": "Product name",
            "dose_annotations": "Dosage details"
        }

    category_choices = [
        ('dry', 'Dry'),
        ('wet', 'Wet'),
        ('supplement', 'Supplement')
    ]

    real_start_date = forms.DateField(required=True, widget=forms.DateInput(attrs={"type": "date", "required": True}))
    real_end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date", "required": False}))

    category = forms.ChoiceField(choices=category_choices, required=True)
    producer = forms.CharField(max_length=120, required=False)
    product_name = forms.CharField(max_length=80, required=True)
    dose_annotations = forms.CharField(max_length=250, required=False)
