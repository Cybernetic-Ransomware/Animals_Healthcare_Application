from __future__ import annotations

from datetime import date

from django.db.models import Q, QuerySet

from ahc.apps.animals.models import Animal, AnimalShare, ShareCategory, ShareDefaults


def _today() -> date:
    return date.today()


def animals_visible_to(profile) -> QuerySet[Animal]:
    """Return all living animals accessible to the given profile (owner or active keeper).

    Deceased animals are excluded unconditionally — they are only accessible to the
    owner via deceased_animals_for().
    """
    today = _today()
    return (
        Animal.objects.filter(date_of_death__isnull=True)
        .filter(
            Q(owner=profile)
            | Q(shares__carer=profile, shares__valid_until__isnull=True)
            | Q(shares__carer=profile, shares__valid_until__gte=today)
        )
        .distinct()
        .order_by("-creation_date")
    )


def deceased_animals_for(profile) -> QuerySet[Animal]:
    """Return deceased animals owned by the profile, ordered by most recently deceased first.

    Carers are intentionally excluded: death withdraws management to the owner only.
    """
    return Animal.objects.filter(owner=profile, date_of_death__isnull=False).order_by("-date_of_death")


def active_share_for(profile, animal: Animal) -> AnimalShare | None:
    """Return the non-expired AnimalShare for this profile/animal pair, or None."""
    today = _today()
    try:
        share = AnimalShare.objects.get(animal=animal, carer=profile)
    except AnimalShare.DoesNotExist:
        return None
    return share if share.is_active(today) else None


def user_can_view_animal(profile, animal: Animal) -> bool:
    """Return True if the profile may view this animal (read-only access).

    The owner may always view — including deceased animals (read-only archive).
    Carers may only view a living animal with an active, non-expired share.
    """
    if animal.owner == profile:
        return True
    if animal.date_of_death is not None:
        return False  # death withdraws all non-owner access
    return active_share_for(profile, animal) is not None


def user_can_modify_animal(profile, animal: Animal) -> bool:
    """Return True if the profile may write to this animal or its records.

    No writes are allowed on a deceased animal — not even by the owner.
    The only permitted mutations on a deceased animal (editing the memorial note and
    un-archiving) use is_animal_owner directly, bypassing this predicate by design.
    """
    if animal.date_of_death is not None:
        return False
    if animal.owner == profile:
        return True
    return active_share_for(profile, animal) is not None


def user_can_access_animal(profile, animal: Animal) -> bool:
    """Alias for user_can_view_animal kept for backward compatibility.

    Prefer user_can_view_animal (read contexts) or user_can_modify_animal (write contexts).
    """
    return user_can_view_animal(profile, animal)


def is_animal_owner(profile, animal: Animal) -> bool:
    """Return True if the profile is the owner of the animal."""
    return animal.owner == profile


def allowed_categories_for(profile, animal: Animal) -> set[str]:
    """Return the set of ShareCategory values the profile may see.

    Owners get all categories.  Carers get only what their active share grants.
    Carers always get an empty set on a deceased animal (death withdraws all carer access).
    An empty set means no data-category access (animal page itself still blocked
    upstream by user_can_view_animal).
    """
    if is_animal_owner(profile, animal):
        return {c.value for c in ShareCategory}
    if animal.date_of_death is not None:
        return set()
    share = active_share_for(profile, animal)
    if share is None:
        return set()
    return share.allowed_categories()


def get_or_create_share_defaults(profile) -> ShareDefaults:
    """Return the owner's ShareDefaults row, creating it with safe defaults if absent."""
    defaults, _ = ShareDefaults.objects.get_or_create(profile=profile)
    return defaults


def animals_for_biometric_batch(profile) -> QuerySet[Animal]:
    """Return all animals the profile may include in a batch biometric session.

    Currently mirrors animals_visible_to (owner or active share with any access),
    matching the permission level of the single-record BiometricRecordCreateView.
    TODO: narrow to allow_biometrics=True for carer shares once that flag is enforced
    consistently across single-record creation too.
    """
    return animals_visible_to(profile)


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
