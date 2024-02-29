from animals.models import Animal
from django import forms
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.db.models import Q


class AnimalRegisterForm(forms.ModelForm):
    class Meta:
        model = Animal
        fields = ["full_name"]

    full_name = forms.CharField(
        validators=[
            MinLengthValidator(limit_value=3, message="Minimum 3 characters required."),
            MaxLengthValidator(limit_value=50, message="Maximum 50 characters allowed."),
        ]
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean_full_name(self):
        full_name = self.cleaned_data.get("full_name")

        if Animal.objects.filter(Q(full_name=full_name) & (Q(owner=self.user) | Q(allowed_users=self.user))).exists():
            raise forms.ValidationError("An animal with that name is already in your care.")

        return full_name


class PinAnimalForm(forms.Form):
    animal_id = forms.CharField(widget=forms.HiddenInput)
    action = forms.CharField(widget=forms.HiddenInput)
