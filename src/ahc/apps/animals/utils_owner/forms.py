from datetime import date

from django import forms
from PIL import Image

from ahc.apps.animals.models import Animal, AnimalShare
from ahc.apps.users.models import Profile


class ImageUploadForm(forms.ModelForm):
    ALLOWED_EXTENSIONS = ["jpg", "jpeg", "png"]
    MAX_IMAGE_SIZE_MB = 5
    MAX_IMAGE_DIMENSION = 1000

    class Meta:
        model = Animal
        fields = ["profile_image"]

    def clean_profile_image(self):
        image = self.cleaned_data.get("profile_image")

        if image:
            extension = image.name.split(".")[-1].lower()
            if extension not in self.ALLOWED_EXTENSIONS:
                raise forms.ValidationError("Invalid file extension.")

        if image and image.size > self.MAX_IMAGE_SIZE_MB * 1024 * 1024:
            raise forms.ValidationError("Image size is too large.")

        if image:
            img = Image.open(image)
            width, height = img.size
            if width > self.MAX_IMAGE_DIMENSION or height > self.MAX_IMAGE_DIMENSION:
                raise forms.ValidationError("Image dimensions are too large.")

        return image


class ChangeOwnerForm(forms.Form):
    new_owner = forms.CharField(max_length=255, required=True, label="New owner's profile name")
    set_keeper = forms.BooleanField(required=False, label="Set as keeper")

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop("instance", None)
        super().__init__(*args, **kwargs)

    def clean_new_owner(self):
        new_owner = self.cleaned_data.get("new_owner")

        if new_owner == self.instance.owner.user.username:
            raise forms.ValidationError("You are already the owner.")

        if not Profile.objects.filter(user__username=new_owner).exists():
            raise forms.ValidationError("User does not exist.")

        new_owner_profile = Profile.objects.get(user__username=new_owner)

        return new_owner_profile


class ManageKeepersForm(forms.Form):
    input_user = forms.CharField(max_length=255, required=True, label="Full keeper profile name")
    valid_until = forms.DateField(
        required=False,
        label="Access expires on (leave empty for indefinite)",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    allow_basic = forms.BooleanField(required=False, label="Basic info")
    allow_vet_contact = forms.BooleanField(required=False, label="Vet contact")
    allow_diet = forms.BooleanField(required=False, label="Diet")
    allow_medications = forms.BooleanField(required=False, label="Medications")
    allow_history = forms.BooleanField(required=False, label="History & notes")
    allow_biometrics = forms.BooleanField(required=False, label="Biometrics")
    allow_vaccinations = forms.BooleanField(required=False, label="Vaccinations")

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop("instance", None)
        super().__init__(*args, **kwargs)
        # Pre-fill category flags from the owner's share defaults.
        from ahc.apps.animals.selectors import get_or_create_share_defaults

        defaults = get_or_create_share_defaults(self.instance.owner)
        for field in (
            "allow_basic",
            "allow_vet_contact",
            "allow_diet",
            "allow_medications",
            "allow_history",
            "allow_biometrics",
            "allow_vaccinations",
        ):
            self.fields[field].initial = getattr(defaults, field)

    def clean_input_user(self):
        input_user = self.cleaned_data.get("input_user")

        if input_user == self.instance.owner.user.username:
            raise forms.ValidationError("As the owner you can not set yourself as a keeper.")

        if self.instance.shares.filter(carer__user__username=input_user).exists():
            raise forms.ValidationError("User is already on the list of keepers.")

        profile = Profile.objects.filter(user__username=input_user).first()
        if profile is None:
            raise forms.ValidationError("User does not exist.")

        return profile.pk


class EditShareForm(forms.ModelForm):
    class Meta:
        model = AnimalShare
        fields = [
            "valid_until",
            "allow_basic",
            "allow_vet_contact",
            "allow_diet",
            "allow_medications",
            "allow_history",
            "allow_biometrics",
            "allow_vaccinations",
        ]
        widgets = {"valid_until": forms.DateInput(attrs={"type": "date"})}
        labels = {
            "valid_until": "Access expires on (leave empty for indefinite)",
            "allow_basic": "Basic info",
            "allow_vet_contact": "Vet contact",
            "allow_diet": "Diet",
            "allow_medications": "Medications",
            "allow_history": "History & notes",
            "allow_biometrics": "Biometrics",
            "allow_vaccinations": "Vaccinations",
        }


class ChangeBirthdayForm(forms.ModelForm):
    class Meta:
        model = Animal
        fields = ["birthdate"]
        widgets = {"birthdate": forms.DateInput(attrs={"type": "date"})}

    def clean_birthdate(self):
        birthdate = self.cleaned_data.get("birthdate")
        current_date = date.today()

        if birthdate is not None and birthdate > current_date:
            raise forms.ValidationError("Date could not be set further than current day.")

        return birthdate


class ChangeFirstContactForm(forms.ModelForm):
    class Meta:
        model = Animal
        fields = ["first_contact_vet", "first_contact_medical_place"]
        widgets = {
            "first_contact_vet": forms.Textarea(attrs={"rows": 4, "cols": 2}),
            "first_contact_medical_place": forms.Textarea(attrs={"rows": 4, "cols": 2}),
        }


class ChangeNextVisitForm(forms.ModelForm):
    class Meta:
        model = Animal
        fields = ["next_visit_date"]
        widgets = {"next_visit_date": forms.DateInput(attrs={"type": "date"})}


class ChangeDietaryRestrictionsForm(forms.ModelForm):
    class Meta:
        model = Animal
        fields = ["dietary_restrictions"]
        widgets = {"dietary_restrictions": forms.Textarea(attrs={"rows": 6, "cols": 2})}


class ChangeAnimalDetailsForm(forms.ModelForm):
    class Meta:
        model = Animal
        fields = ["species", "breed", "sex", "sterilization"]
