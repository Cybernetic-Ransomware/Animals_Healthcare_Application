from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile
from django.db import transaction

from ahc.apps.animals.models import Animal
from ahc.apps.animals.signals import update_allowed_users


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


@pytest.mark.integration
@pytest.mark.django_db
class TestRemoveOldPicturesAfterAnimalDeleteSignal:
    """remove_old_pictures_after_animal_delete: transaction-safe targeted delete."""

    @pytest.fixture(autouse=True)
    def _media_root(self, tmp_path, settings):
        settings.MEDIA_ROOT = tmp_path
        (tmp_path / "profile_pics" / "animals").mkdir(parents=True)

    def test_custom_image_removed_after_commit(self, django_capture_on_commit_callbacks, animal):
        animal.profile_image.save("rex.png", ContentFile(b"fake-image-bytes"), save=True)
        image_path = Path(animal.profile_image.path)
        assert image_path.exists()

        with django_capture_on_commit_callbacks(execute=True):
            animal.delete()

        assert not image_path.exists()

    def test_blank_image_delete_does_not_unlink_files(self, django_capture_on_commit_callbacks, animal, tmp_path):
        assert animal.profile_image.name == ""

        # Proves the guard short-circuits on the blank name before touching disk at all.
        sentinel = tmp_path / "profile_pics" / "animals" / "sentinel.png"
        sentinel.write_bytes(b"unrelated-file-bytes")

        with (
            patch.object(Path, "unlink") as mock_unlink,
            django_capture_on_commit_callbacks(execute=True),
        ):
            animal.delete()

        mock_unlink.assert_not_called()
        assert sentinel.exists()

    def test_missing_file_on_disk_does_not_raise(self, django_capture_on_commit_callbacks, animal):
        animal.profile_image.save("rex.png", ContentFile(b"fake-image-bytes"), save=True)
        Path(animal.profile_image.path).unlink()

        with django_capture_on_commit_callbacks(execute=True):
            animal.delete()

    def test_callback_failure_does_not_propagate_and_record_stays_deleted(self, django_capture_on_commit_callbacks, animal):
        animal.profile_image.save("rex.png", ContentFile(b"fake-image-bytes"), save=True)
        animal_id = animal.id

        with (
            patch.object(Path, "unlink", side_effect=PermissionError("simulated")),
            django_capture_on_commit_callbacks(execute=True),
        ):
            animal.delete()

        assert not Animal.objects.filter(id=animal_id).exists()

    def test_rollback_keeps_record_and_file(self, animal):
        animal.profile_image.save("rex.png", ContentFile(b"fake-image-bytes"), save=True)
        image_path = Path(animal.profile_image.path)
        animal_id = animal.id

        class _Boom(Exception):
            pass

        with pytest.raises(_Boom), transaction.atomic():
            animal.delete()
            raise _Boom()

        assert Animal.objects.filter(id=animal_id).exists()
        assert image_path.exists()
