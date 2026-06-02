from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from ahc.apps.animals.models import ShareDefaults
from ahc.apps.users.models import Profile


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ["username", "email"]


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["profile_image"]


class ShareDefaultsForm(forms.ModelForm):
    class Meta:
        model = ShareDefaults
        fields = [
            "allow_basic",
            "allow_vet_contact",
            "allow_diet",
            "allow_medications",
            "allow_history",
            "allow_biometrics",
            "allow_vaccinations",
        ]
        labels = {
            "allow_basic": "Basic info",
            "allow_vet_contact": "Vet contact",
            "allow_diet": "Diet",
            "allow_medications": "Medications",
            "allow_history": "History & notes",
            "allow_biometrics": "Biometrics",
            "allow_vaccinations": "Vaccinations",
        }
