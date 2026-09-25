from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.core.files.base import ContentFile
from django.db import transaction

from ahc.apps.users.models import Profile
from ahc.apps.users.signals import create_background, create_basic_privilege


@pytest.mark.integration
@pytest.mark.django_db
class TestRemoveOldPicturesAfterProfileDeleteSignal:
    """remove_old_pictures_after_profile_delete: transaction-safe targeted delete."""

    @pytest.fixture(autouse=True)
    def _media_root(self, tmp_path, settings):
        settings.MEDIA_ROOT = tmp_path
        (tmp_path / "profile_pics" / "users").mkdir(parents=True)

    def test_custom_image_removed_after_commit(self, django_capture_on_commit_callbacks, user_profile):
        _, profile = user_profile
        profile.profile_image.save("avatar.png", ContentFile(b"fake-image-bytes"), save=True)
        image_path = Path(profile.profile_image.path)
        assert image_path.exists()

        with django_capture_on_commit_callbacks(execute=True):
            profile.delete()

        assert not image_path.exists()

    def test_blank_image_delete_does_not_unlink_files(self, django_capture_on_commit_callbacks, user_profile, tmp_path):
        _, profile = user_profile
        assert profile.profile_image.name == ""

        # Proves the guard short-circuits on the blank name before touching disk at all.
        sentinel = tmp_path / "profile_pics" / "users" / "sentinel.png"
        sentinel.write_bytes(b"unrelated-file-bytes")

        with (
            patch.object(Path, "unlink") as mock_unlink,
            django_capture_on_commit_callbacks(execute=True),
        ):
            profile.delete()

        mock_unlink.assert_not_called()
        assert sentinel.exists()

    def test_missing_file_on_disk_does_not_raise(self, django_capture_on_commit_callbacks, user_profile):
        _, profile = user_profile
        profile.profile_image.save("avatar.png", ContentFile(b"fake-image-bytes"), save=True)
        Path(profile.profile_image.path).unlink()

        with django_capture_on_commit_callbacks(execute=True):
            profile.delete()

    def test_callback_failure_does_not_propagate_and_record_stays_deleted(
        self, django_capture_on_commit_callbacks, user_profile
    ):
        _, profile = user_profile
        profile.profile_image.save("avatar.png", ContentFile(b"fake-image-bytes"), save=True)
        profile_id = profile.id

        with (
            patch.object(Path, "unlink", side_effect=PermissionError("simulated")),
            django_capture_on_commit_callbacks(execute=True),
        ):
            profile.delete()

        assert not Profile.objects.filter(id=profile_id).exists()

    def test_user_delete_cascade_removes_profile_image(self, django_capture_on_commit_callbacks, user_profile):
        user, profile = user_profile
        profile.profile_image.save("avatar.png", ContentFile(b"fake-image-bytes"), save=True)
        image_path = Path(profile.profile_image.path)
        assert image_path.exists()

        with django_capture_on_commit_callbacks(execute=True):
            user.delete()

        assert not image_path.exists()
        assert not Profile.objects.filter(pk=profile.pk).exists()

    def test_rollback_keeps_record_and_file(self, user_profile):
        _, profile = user_profile
        profile.profile_image.save("avatar.png", ContentFile(b"fake-image-bytes"), save=True)
        image_path = Path(profile.profile_image.path)
        profile_id = profile.id

        class _Boom(Exception):
            pass

        with pytest.raises(_Boom), transaction.atomic():
            profile.delete()
            raise _Boom()

        assert Profile.objects.filter(id=profile_id).exists()
        assert image_path.exists()


@pytest.mark.unit
class TestCreateBasicPrivilegeSignal:
    """create_basic_privilege: assigns Empty Privilege when profile has none."""

    def test_assigns_privilege_when_missing(self):
        privilege_mock = MagicMock()
        instance = MagicMock(spec=Profile)
        instance.privilege_tier = None

        with patch("ahc.apps.users.signals.Privilege.objects.get_or_create", return_value=(privilege_mock, True)):
            create_basic_privilege(sender=Profile, instance=instance)

        assert instance.privilege_tier is privilege_mock

    def test_skips_when_privilege_already_set(self):
        instance = MagicMock(spec=Profile)
        instance.privilege_tier = MagicMock()

        with patch("ahc.apps.users.signals.Privilege.objects.get_or_create") as mock_goc:
            create_basic_privilege(sender=Profile, instance=instance)

        mock_goc.assert_not_called()


@pytest.mark.unit
class TestCreateBackgroundSignal:
    """create_background: assigns Default Background when profile has none."""

    def test_assigns_background_when_missing(self):
        background_mock = MagicMock()
        instance = MagicMock(spec=Profile)
        instance.profile_background = None

        with patch("ahc.apps.users.signals.ProfileBackground.objects.get_or_create", return_value=(background_mock, True)):
            create_background(sender=Profile, instance=instance)

        assert instance.profile_background is background_mock

    def test_skips_when_background_already_set(self):
        instance = MagicMock(spec=Profile)
        instance.profile_background = MagicMock()

        with patch("ahc.apps.users.signals.ProfileBackground.objects.get_or_create") as mock_goc:
            create_background(sender=Profile, instance=instance)

        mock_goc.assert_not_called()
