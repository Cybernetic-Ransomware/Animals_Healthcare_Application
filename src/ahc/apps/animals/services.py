from __future__ import annotations

from datetime import date

from django.shortcuts import get_object_or_404
from PIL import Image

from ahc.apps.animals.models import Animal, AnimalShare
from ahc.apps.animals.selectors import get_or_create_share_defaults, user_can_access_animal


def create_animal(owner_profile, form) -> Animal:
    """Create a new animal owned by owner_profile from a validated form instance."""
    animal = form.save(commit=False)
    animal.owner = owner_profile
    animal.save()
    return animal


def pin_animal(profile, animal_id) -> None:
    """Pin an animal for the given profile.

    Raises PermissionError when the profile has no read access to the animal.
    """
    animal = get_object_or_404(Animal, id=animal_id)
    if not user_can_access_animal(profile, animal):
        raise PermissionError("You do not have access to this animal.")
    profile.pinned_animals.add(animal)


def unpin_animal(profile, animal_id) -> None:
    """Remove an animal from the profile's pinned list."""
    profile.pinned_animals.remove(animal_id)


def process_profile_image(animal: Animal) -> None:
    """Resize the animal's profile image to at most 448x448 pixels."""
    img = Image.open(animal.profile_image.path)
    if img.height > 448 or img.width > 448:
        img.thumbnail((448, 448))
        img.save(animal.profile_image.path)


def transfer_ownership(animal: Animal, new_owner, set_keeper: bool, requesting_profile) -> None:
    """Transfer animal ownership to new_owner.

    If set_keeper is True, the previous owner (requesting_profile) is added as a carer
    with an AnimalShare that mirrors their ShareDefaults.
    """
    animal.owner = new_owner
    animal.save()
    if set_keeper:
        create_share(animal, requesting_profile.pk, scope=None, valid_until=None)


def create_share(animal: Animal, carer_id, scope: dict | None, valid_until: date | None) -> AnimalShare:
    """Create (or update) an AnimalShare for the given carer.

    When scope is None, the access flags are copied from the animal owner's ShareDefaults.
    scope, when provided, is a dict mapping allow_* field names to bool values.
    """
    if scope is None:
        defaults = get_or_create_share_defaults(animal.owner)
        scope = {
            "allow_basic": defaults.allow_basic,
            "allow_vet_contact": defaults.allow_vet_contact,
            "allow_diet": defaults.allow_diet,
            "allow_medications": defaults.allow_medications,
            "allow_history": defaults.allow_history,
            "allow_biometrics": defaults.allow_biometrics,
        }

    share, _ = AnimalShare.objects.update_or_create(
        animal=animal,
        carer_id=carer_id,
        defaults={"valid_until": valid_until, **scope},
    )
    return share


def update_share(share: AnimalShare, scope: dict, valid_until: date | None) -> None:
    """Update the access scope and expiry date of an existing AnimalShare."""
    for field, value in scope.items():
        setattr(share, field, value)
    share.valid_until = valid_until
    share.save()


def add_keeper(animal: Animal, keeper_id) -> None:
    """Add a keeper to the animal's shares using the owner's default scope."""
    create_share(animal, keeper_id, scope=None, valid_until=None)


def set_birthday(animal: Animal, birthdate) -> None:
    """Update the animal's birthdate."""
    animal.birthdate = birthdate
    animal.save()


def set_first_contact(animal: Animal, vet: str, place: str) -> None:
    """Update the animal's first-contact vet name and medical place."""
    animal.first_contact_vet = vet
    animal.first_contact_medical_place = place
    animal.save()


def set_next_visit(animal: Animal, next_visit_date) -> None:
    """Set or clear the animal's next scheduled vet visit date."""
    animal.next_visit_date = next_visit_date
    animal.save()


def set_dietary_restrictions(animal: Animal, restrictions: str) -> None:
    """Update the animal's dietary restrictions / things to avoid."""
    animal.dietary_restrictions = restrictions
    animal.save()


def set_animal_details(
    animal: Animal, species: str | None, breed: str | None, sex: str | None, sterilization: bool
) -> None:
    """Update the animal's species, breed, sex and sterilization status."""
    animal.species = species
    animal.breed = breed
    animal.sex = sex
    animal.sterilization = sterilization
    animal.save()


def remove_keeper(animal: Animal, keeper_id) -> None:
    """Remove a keeper from the animal's shares by Profile PK."""
    AnimalShare.objects.filter(animal=animal, carer_id=keeper_id).delete()


def set_deceased(animal: Animal, date_of_death: date, memorial_note: str | None) -> None:
    """Record an animal as deceased.

    AnimalShare rows are intentionally left intact (soft withdrawal).  The deceased
    gate in the selectors makes all shares inert while date_of_death is set, and
    un-archiving with unset_deceased instantly restores the prior access configuration.
    """
    animal.date_of_death = date_of_death
    animal.memorial_note = memorial_note
    animal.save()


def set_memorial_note(animal: Animal, memorial_note: str | None) -> None:
    """Update the memorial note on a deceased animal without changing the death date."""
    animal.memorial_note = memorial_note
    animal.save()


def unset_deceased(animal: Animal) -> None:
    """Reverse an archiving action — the animal becomes living again.

    The memorial_note is preserved so that re-archiving retains historical context.
    Existing AnimalShare rows are immediately effective again because the deceased gate
    only checks date_of_death__isnull.
    """
    animal.date_of_death = None
    animal.save()
