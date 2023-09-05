from django import forms
from PIL import Image
from datetime import date

from users.models import Profile
from ..models import Animal


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

        if image:
            if image.size > self.MAX_IMAGE_SIZE_MB * 1024 * 1024:
                raise forms.ValidationError("Image size is too large.")

        if image:
            img = Image.open(image)
            width, height = img.size
            if width > self.MAX_IMAGE_DIMENSION or height > self.MAX_IMAGE_DIMENSION:
                raise forms.ValidationError("Image dimensions are too large.")

        return image


class ChangeOwnerForm(forms.Form):
    new_owner = forms.CharField(
        max_length=255, required=True, label="New owner's profile name"
    )
    set_keeper = forms.BooleanField(required=False, label="Set as keeper")

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop("instance", None)
        super().__init__(*args, **kwargs)

    def clean_new_owner(self):
        new_owner = self.cleaned_data.get("new_owner")
        print(self.cleaned_data.keys())

        if new_owner == self.instance.owner.user.username:
            raise forms.ValidationError("You are already the owner.")

        if not Profile.objects.filter(user__username=new_owner).exists():
            raise forms.ValidationError("User does not exist.")

        new_owner_profile = Profile.objects.get(user__username=new_owner)

        return new_owner_profile


class ManageKeepersForm(forms.Form):
    input_user = forms.CharField(
        max_length=255, required=True, label="Full keeper profile name"
    )

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop("instance", None)
        super().__init__(*args, **kwargs)

    def clean_input_user(self):
        input_user = self.cleaned_data.get("input_user")

        if input_user == self.instance.owner.user.username:
            raise forms.ValidationError(
                "As the owner you can not set yourself as a keeper."
            )

        if input_user in self.instance.allowed_users.all():
            raise forms.ValidationError("User is already on the list of keepers.")

        if not Profile.objects.filter(user__username=input_user).exists():
            raise forms.ValidationError("User does not exist.")

        input_user_id = Profile.objects.filter(user__username=input_user).first().id

        return input_user_id


class ChangeBirthdayForm(forms.ModelForm):
    class Meta:
        model = Animal
        fields = ["birthdate"]
        widgets = {
            "birthdate": forms.DateInput(attrs={"type": "date"})
        }

    def clean_birthdate(self):
        birthdate = self.cleaned_data.get("birthdate")
        current_date = date.today()

        if birthdate > current_date:
            raise forms.ValidationError("Date could not be set further than current day.")

        return birthdate
