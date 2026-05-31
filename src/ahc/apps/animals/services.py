from __future__ import annotations

from django.shortcuts import get_object_or_404
from PIL import Image

from ahc.apps.animals.models import Animal
from ahc.apps.animals.selectors import user_can_access_animal


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

    If set_keeper is True, the previous owner (requesting_profile) is added to allowed_users.
    """
    animal.owner = new_owner
    animal.save()
    if set_keeper:
        animal.allowed_users.add(requesting_profile)


def add_keeper(animal: Animal, keeper_id) -> None:
    """Add a keeper to the animal's allowed_users list by Profile PK."""
    animal.allowed_users.add(keeper_id)


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
    """Remove a keeper from the animal's allowed_users list by Profile PK."""
    animal.allowed_users.remove(keeper_id)
