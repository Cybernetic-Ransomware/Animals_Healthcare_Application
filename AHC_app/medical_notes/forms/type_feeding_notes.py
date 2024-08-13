from django import forms
from django.conf import settings
from medical_notes.models.type_feeding_notes import EmailNotification, FeedingNote
from timezone_field import TimeZoneFormField


class DietRecordForm(forms.ModelForm):
    class Meta:
        model = FeedingNote
        fields = [
            "real_start_date",
            "real_end_date",
            "category",
            "producer",
            "product_name",
            "dose_annotations",
        ]
        labels = {
            "real_start_date": "Actual start date of feeding",
            "real_end_date": "Actual end date of feeding",
            "category": "Category",
            "producer": "Producer",
            "product_name": "Product name",
            "dose_annotations": "Dosage details",
        }

    category_choices = [("dry", "Dry"), ("wet", "Wet"), ("supplement", "Supplement")]

    real_start_date = forms.DateField(required=True, widget=forms.DateInput(attrs={"type": "date", "required": True}))
    real_end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "required": False}),
    )

    category = forms.ChoiceField(choices=category_choices, required=True)
    producer = forms.CharField(max_length=120, required=False)
    product_name = forms.CharField(max_length=80, required=True)
    dose_annotations = forms.CharField(max_length=250, required=False)


class NotificationRecordForm(forms.ModelForm):
    class Meta:
        model = EmailNotification
        fields = [
            "email",
            "description",
            "is_active",
            "message",
            "start_date",
            "end_date",
            "timezone",
            "daily_timestamp",
        ]
        labels = {
            "email": "E-mail address",
            "description": "Short description",
            "is_active": "Activate",
            "message": "Message",
            "start_date": "Start subscription",
            "end_date": "End subscription",
            "daily_timestamp": "Time of sending",
            "timezone": "Receiver time zone",
        }

    days_of_week_choices = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    timezone = TimeZoneFormField(choices_display="WITH_GMT_OFFSET")

    days_of_week = forms.MultipleChoiceField(choices=days_of_week_choices, widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, **kwargs):
        super(NotificationRecordForm, self).__init__(*args, **kwargs)

        self.fields["timezone"].initial = str(settings.TIME_ZONE)
