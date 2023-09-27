import uuid

from django.db import models
from users.models import Profile as UserProfile


class Animal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=50, null=False, blank=False)
    short_description = models.CharField(max_length=250, default=None, blank=True, null=True)
    long_description = models.CharField(max_length=2500, default=None, blank=True, null=True)

    birthdate = models.DateField(null=True, default=None)
    profile_image = models.ImageField(
        default="profile_pics/pet-care.png", upload_to="profile_pics/animals"
    )
    creation_date = models.DateTimeField(auto_now_add=True, editable=False)

    owner = models.ForeignKey(
        UserProfile, on_delete=models.SET_NULL, null=True, related_name='owner'
    )  # dodac okresową notyfikację o braku ownera - przypisuje admin z panelu
    allowed_users = models.ManyToManyField(UserProfile, related_name='keepers')

    first_contact_vet = models.CharField(max_length=250, default=None, blank=True, null=True)
    # first_contact_vet = models.ForeignKey(Vet_pofile)
    first_contact_medical_place = models.CharField(max_length=250, default=None, blank=True, null=True)
    # first_contact_medical_place = models.ForeignKey(Place_profile)

    last_control_visit = models.DateTimeField(null=True, default=None)


# biometric_records_history = # relacja jeden do jeden w notatce
# medical_records_history = None  # relacja jeden do jeden do notatki
# feeding_records_history = None # relacja jeden do jeden w notatce
