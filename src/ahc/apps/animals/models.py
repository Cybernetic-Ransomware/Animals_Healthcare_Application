from __future__ import annotations

import uuid
from datetime import date

from django.db import models

from ahc.apps.users.models import Profile as UserProfile


class Sex(models.TextChoices):
    MALE = "m", "Male"
    FEMALE = "f", "Female"


class ShareCategory(models.TextChoices):
    BASIC = "basic", "Basic info"
    VET_CONTACT = "vet_contact", "Vet contact"
    DIET = "diet", "Diet"
    MEDICATIONS = "medications", "Medications"
    HISTORY = "history", "History & notes"
    BIOMETRICS = "biometrics", "Biometrics"
    VACCINATIONS = "vaccinations", "Vaccinations"


class Animal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=50, null=False, blank=False)
    short_description = models.CharField(max_length=250, default=None, blank=True, null=True)
    long_description = models.CharField(max_length=2500, default=None, blank=True, null=True)

    birthdate = models.DateField(null=True, default=None)
    profile_image = models.ImageField(default="profile_pics/pet-care.png", upload_to="profile_pics/animals")
    creation_date = models.DateTimeField(auto_now_add=True, editable=False)

    owner = models.ForeignKey(
        UserProfile, on_delete=models.SET_NULL, null=True, related_name="owner"
    )  # dodac okresową notyfikację o braku ownera - przypisuje admin z panelu
    allowed_users = models.ManyToManyField(UserProfile, through="AnimalShare", related_name="keepers")

    first_contact_vet = models.CharField(max_length=250, default=None, blank=True, null=True)
    # first_contact_vet = models.ForeignKey(Vet_pofile)
    first_contact_medical_place = models.CharField(max_length=250, default=None, blank=True, null=True)
    # first_contact_medical_place = models.ForeignKey(Place_profile)

    last_control_visit = models.DateTimeField(null=True, default=None)

    next_visit_date = models.DateField(null=True, blank=True, default=None)

    dietary_restrictions = models.CharField(max_length=2500, null=True, blank=True, default=None)

    species = models.CharField(max_length=100, default=None, blank=True, null=True)
    breed = models.CharField(max_length=100, default=None, blank=True, null=True)
    sex = models.CharField(max_length=1, choices=Sex.choices, default=None, blank=True, null=True)
    sterilization = models.BooleanField(default=False)

    date_of_death = models.DateField(default=None, blank=True, null=True)
    memorial_note = models.CharField(max_length=2500, default=None, blank=True, null=True)

    @property
    def is_deceased(self) -> bool:
        """Return True if a date of death has been recorded for this animal."""
        return self.date_of_death is not None


class AnimalShare(models.Model):
    """Through model for Animal.allowed_users — stores per-share access scope and expiry."""

    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name="shares")
    carer = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="received_shares")
    created = models.DateTimeField(auto_now_add=True, editable=False)
    valid_until = models.DateField(default=None, blank=True, null=True)

    allow_basic = models.BooleanField(default=False)
    allow_vet_contact = models.BooleanField(default=False)
    allow_diet = models.BooleanField(default=False)
    allow_medications = models.BooleanField(default=False)
    allow_history = models.BooleanField(default=False)
    allow_biometrics = models.BooleanField(default=False)
    allow_vaccinations = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["animal", "carer"], name="uniq_animal_carer_share")]

    def allowed_categories(self) -> set[str]:
        """Return the set of ShareCategory values this share grants access to."""
        mapping = {
            "allow_basic": ShareCategory.BASIC,
            "allow_vet_contact": ShareCategory.VET_CONTACT,
            "allow_diet": ShareCategory.DIET,
            "allow_medications": ShareCategory.MEDICATIONS,
            "allow_history": ShareCategory.HISTORY,
            "allow_biometrics": ShareCategory.BIOMETRICS,
            "allow_vaccinations": ShareCategory.VACCINATIONS,
        }
        return {value for attr, value in mapping.items() if getattr(self, attr)}

    def is_active(self, today: date | None = None) -> bool:
        """Return True if the share has not yet expired."""
        if today is None:
            today = date.today()
        return self.valid_until is None or self.valid_until >= today


class ShareDefaults(models.Model):
    """Per-owner template that pre-fills the access scope when a new share is created."""

    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name="share_defaults")
    allow_basic = models.BooleanField(default=True)
    allow_vet_contact = models.BooleanField(default=False)
    allow_diet = models.BooleanField(default=False)
    allow_medications = models.BooleanField(default=False)
    allow_history = models.BooleanField(default=False)
    allow_biometrics = models.BooleanField(default=False)
    allow_vaccinations = models.BooleanField(default=False)
