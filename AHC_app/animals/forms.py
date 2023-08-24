from django import forms
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.db.models import Q
from PIL import Image

from .models import Animal
from users.models import Profile


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

        if Animal.objects.filter(Q(full_name=full_name) & (Q(owner=self.user) | Q(allowed_users=self.user))).exists():
            raise forms.ValidationError("An animal with that name is already in your care.")

        return full_name


class ImageUploadForm(forms.ModelForm):
    ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png']
    MAX_IMAGE_SIZE_MB = 5
    MAX_IMAGE_DIMENSION = 1000

    class Meta:
        model = Animal
        fields = ['profile_image']

    def clean_profile_image(self):
        image = self.cleaned_data.get('profile_image')

        if image:
            extension = image.name.split('.')[-1].lower()
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


class ManageKeepersForm(forms.ModelForm):
    input_user = forms.CharField(max_length=255, required=True, label="Full keeper profile name")

    class Meta:
        model = Animal
        fields = ['allowed_users']

    def clean_input_user(self):
        input_user = self.cleaned_data.get('input_user')

        if input_user == self.instance.owner:
            raise forms.ValidationError("As the owner you can not set yourself as a keeper.")

        if input_user in self.instance.allowed_users.all():
            raise forms.ValidationError("User is already on the list of keepers.")

        if not Profile.objects.filter(user__username=input_user).exists():
            raise forms.ValidationError("User does not exist.")
        return input_user
