from django import forms
from django.core.validators import MinLengthValidator, MaxLengthValidator

from .models import Animal


class AnimalRegisterForm(forms.ModelForm):
    class Meta:
        model = Animal
        fields = ["full_name"]

    full_name = forms.CharField(
        validators=[
            MinLengthValidator(limit_value=3, message='Minimum 3 characters required.'),
            MaxLengthValidator(limit_value=50, message='Maximum 50 characters allowed.')
        ]
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_full_name(self):
        full_name = self.cleaned_data.get('full_name')
        if Animal.objects.filter(full_name=full_name).exists():
            animals_data = Animal.objects.filter(full_name=full_name).only('owner', 'allowed_users')

            for animal in animals_data:
                if self.user == animal.owner or self.user in animal.allowed_users.all():
                    raise forms.ValidationError("Animal name in now under your management.")
        return full_name


class AnimalUpdateForm(forms.ModelForm):
    pass
