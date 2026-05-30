import pytest

from ahc.apps.animals.models import Animal
from ahc.apps.animals.signals import update_allowed_users


@pytest.fixture
def animal(db, user_profile):
    _, profile = user_profile
    return Animal.objects.create(full_name="Whiskers", owner=profile)


@pytest.mark.integration
@pytest.mark.django_db
class TestAnimalModel:
    def test_animal_is_created_with_uuid_pk(self, animal):
        assert animal.id is not None
        assert animal.full_name == "Whiskers"

    def test_owner_is_assigned(self, animal, user_profile):
        _, profile = user_profile
        assert animal.owner == profile

    def test_no_keepers_by_default(self, animal):
        assert animal.allowed_users.count() == 0

    def test_second_user_can_be_added_as_keeper(self, animal, second_user_profile):
        _, other_profile = second_user_profile
        animal.allowed_users.add(other_profile)
        assert animal.allowed_users.filter(pk=other_profile.pk).exists()


@pytest.mark.integration
@pytest.mark.django_db
class TestUpdateAllowedUsersSignalHandler:
    """update_allowed_users: owner must not appear in allowed_users."""

    def test_owner_removed_when_present_in_allowed_users(self, animal, user_profile):
        _, profile = user_profile
        animal.allowed_users.add(profile)
        assert animal.allowed_users.filter(pk=profile.pk).exists()

        update_allowed_users(sender=Animal, instance=animal)

        assert not animal.allowed_users.filter(pk=profile.pk).exists()

    def test_non_owner_keeper_not_affected(self, animal, second_user_profile):
        _, other_profile = second_user_profile
        animal.allowed_users.add(other_profile)

        update_allowed_users(sender=Animal, instance=animal)

        assert animal.allowed_users.filter(pk=other_profile.pk).exists()

    def test_no_op_when_allowed_users_is_empty(self, animal):
        update_allowed_users(sender=Animal, instance=animal)
        assert animal.allowed_users.count() == 0
