from __future__ import annotations

from datetime import date

from django.db.models import Q, QuerySet

from ahc.apps.animals.models import Animal, AnimalShare, ShareCategory, ShareDefaults


def _today() -> date:
    return date.today()


def animals_visible_to(profile) -> QuerySet[Animal]:
    """Return all animals accessible to the given profile (owner or active keeper)."""
    today = _today()
    return (
        Animal.objects.filter(
            Q(owner=profile)
            | Q(shares__carer=profile, shares__valid_until__isnull=True)
            | Q(shares__carer=profile, shares__valid_until__gte=today)
        )
        .distinct()
        .order_by("-creation_date")
    )


def active_share_for(profile, animal: Animal) -> AnimalShare | None:
    """Return the non-expired AnimalShare for this profile/animal pair, or None."""
    today = _today()
    try:
        share = AnimalShare.objects.get(animal=animal, carer=profile)
    except AnimalShare.DoesNotExist:
        return None
    return share if share.is_active(today) else None


def user_can_access_animal(profile, animal: Animal) -> bool:
    """Return True if the profile is the owner or holds an active (non-expired) share."""
    if animal.owner == profile:
        return True
    return active_share_for(profile, animal) is not None


def is_animal_owner(profile, animal: Animal) -> bool:
    """Return True if the profile is the owner of the animal."""
    return animal.owner == profile


def allowed_categories_for(profile, animal: Animal) -> set[str]:
    """Return the set of ShareCategory values the profile may see.

    Owners get all categories.  Carers get only what their active share grants.
    An empty set means no data-category access (animal page itself still blocked
    upstream by user_can_access_animal).
    """
    if is_animal_owner(profile, animal):
        return {c.value for c in ShareCategory}
    share = active_share_for(profile, animal)
    if share is None:
        return set()
    return share.allowed_categories()


def get_or_create_share_defaults(profile) -> ShareDefaults:
    """Return the owner's ShareDefaults row, creating it with safe defaults if absent."""
    defaults, _ = ShareDefaults.objects.get_or_create(profile=profile)
    return defaults


def is_pinned(profile, animal: Animal) -> bool:
    """Return True if the animal is currently pinned by the given profile."""
    return profile.pinned_animals.filter(pk=animal.pk).exists()


def recent_records_for(animal: Animal, limit: int = 5) -> QuerySet:
    """Return the most recent MedicalRecords for the animal, newest first."""
    from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord

    return MedicalRecord.objects.filter(animal=animal).order_by("-date_creation")[:limit]


def profile_by_username(username: str):
    """Return the Profile for the given username, or None if not found."""
    from ahc.apps.users.models import Profile

    return Profile.objects.filter(user__username=username).first()
