from bootstrap_modal_forms.forms import BSModalForm
from django import forms
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.db.models import Q
from PIL import Image
from users.models import Profile

from .models import Animal


class AnimalRegisterForm(forms.ModelForm):
    class Meta:
        model = Animal
        fields = ["full_name"]

    full_name = forms.CharField(
        validators=[
            MinLengthValidator(limit_value=3, message="Minimum 3 characters required."),
            MaxLengthValidator(
                limit_value=50, message="Maximum 50 characters allowed."
            ),
        ]
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean_full_name(self):
        full_name = self.cleaned_data.get("full_name")

        if Animal.objects.filter(
            Q(full_name=full_name) & (Q(owner=self.user) | Q(allowed_users=self.user))
        ).exists():
            raise forms.ValidationError(
                "An animal with that name is already in your care."
            )

        return full_name


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


class ChangeOwnerForm(BSModalForm):
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
