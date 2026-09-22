import shutil
from pathlib import Path

import pytest
from django.core.files.base import ContentFile

from ahc.apps.animals.models import Animal
from celery_notifications.cron import _clean_orphaned_images, clean_orphaned_profile_images


def _basename(field_name: str | None) -> str:
    assert field_name is not None
    return Path(field_name).name


@pytest.mark.unit
class TestCleanOrphanedImagesHelper:
    """_clean_orphaned_images: pure filesystem helper, no DB."""

    def test_orphan_file_removed(self, tmp_path):
        (tmp_path / "orphan.png").write_bytes(b"x")

        removed = _clean_orphaned_images(tmp_path, live_names=set())

        assert removed == 1
        assert not (tmp_path / "orphan.png").exists()

    def test_live_file_kept(self, tmp_path):
        (tmp_path / "live.png").write_bytes(b"x")

        removed = _clean_orphaned_images(tmp_path, live_names={"live.png"})

        assert removed == 0
        assert (tmp_path / "live.png").exists()

    def test_missing_directory_is_a_no_op(self, tmp_path):
        missing = tmp_path / "does-not-exist"

        assert _clean_orphaned_images(missing, live_names=set()) == 0

    def test_unexpected_subdirectory_is_skipped_not_deleted(self, tmp_path):
        (tmp_path / "orphan.png").write_bytes(b"x")
        (tmp_path / "stray-subdir").mkdir()
        (tmp_path / "stray-subdir" / "nested.png").write_bytes(b"x")

        removed = _clean_orphaned_images(tmp_path, live_names=set())

        assert removed == 1
        assert not (tmp_path / "orphan.png").exists()
        assert (tmp_path / "stray-subdir").is_dir()

    def test_mixed_live_and_orphan_files(self, tmp_path):
        (tmp_path / "live.png").write_bytes(b"x")
        (tmp_path / "orphan1.png").write_bytes(b"x")
        (tmp_path / "orphan2.png").write_bytes(b"x")

        removed = _clean_orphaned_images(tmp_path, live_names={"live.png"})

        assert removed == 2
        assert (tmp_path / "live.png").exists()
        assert not (tmp_path / "orphan1.png").exists()
        assert not (tmp_path / "orphan2.png").exists()


@pytest.mark.integration
@pytest.mark.django_db
class TestCleanOrphanedProfileImagesTask:
    """clean_orphaned_profile_images: end-to-end sweep across Animal + Profile, through the real decorator."""

    @pytest.fixture(autouse=True)
    def _media_root(self, tmp_path, settings, monkeypatch):
        settings.MEDIA_ROOT = tmp_path
        (tmp_path / "profile_pics" / "animals").mkdir(parents=True)
        (tmp_path / "profile_pics" / "users").mkdir(parents=True)
        # Relative "logs/cron.log" in logger_config.json resolves against cwd — keep it off the real repo.
        monkeypatch.chdir(tmp_path)

    def _run(self) -> None:
        clean_orphaned_profile_images()

    def test_setup_logging_creates_log_dir_and_task_still_runs(self, tmp_path, user_profile):
        _, profile = user_profile
        profile.profile_image.save("avatar.png", ContentFile(b"fake"), save=True)
        live_name = _basename(profile.profile_image.name)

        self._run()

        assert (tmp_path / "logs" / "cron.log").exists()
        assert (tmp_path / "profile_pics" / "users" / live_name).exists()

    def test_live_animal_image_kept_orphan_removed(self, tmp_path, user_profile):
        _, profile = user_profile
        animal = Animal.objects.create(full_name="Rex", owner=profile)
        animal.profile_image.save("rex.png", ContentFile(b"fake"), save=True)
        live_name = _basename(animal.profile_image.name)

        orphan = tmp_path / "profile_pics" / "animals" / "orphan.png"
        orphan.write_bytes(b"fake")

        self._run()

        assert (tmp_path / "profile_pics" / "animals" / live_name).exists()
        assert not orphan.exists()

    def test_live_profile_image_kept_orphan_removed(self, tmp_path, user_profile):
        _, profile = user_profile
        profile.profile_image.save("avatar.png", ContentFile(b"fake"), save=True)
        live_name = _basename(profile.profile_image.name)

        orphan = tmp_path / "profile_pics" / "users" / "orphan.png"
        orphan.write_bytes(b"fake")

        self._run()

        assert (tmp_path / "profile_pics" / "users" / live_name).exists()
        assert not orphan.exists()

    def test_missing_animals_directory_is_a_no_op_for_that_side(self, tmp_path, user_profile):
        shutil.rmtree(tmp_path / "profile_pics" / "animals")
        _, profile = user_profile
        profile.profile_image.save("avatar.png", ContentFile(b"fake"), save=True)
        live_name = _basename(profile.profile_image.name)

        self._run()

        assert (tmp_path / "profile_pics" / "users" / live_name).exists()

    def test_missing_users_directory_is_a_no_op_for_that_side(self, tmp_path, user_profile):
        shutil.rmtree(tmp_path / "profile_pics" / "users")
        _, profile = user_profile
        animal = Animal.objects.create(full_name="Rex", owner=profile)
        animal.profile_image.save("rex.png", ContentFile(b"fake"), save=True)
        live_name = _basename(animal.profile_image.name)

        self._run()

        assert (tmp_path / "profile_pics" / "animals" / live_name).exists()

    def test_replacement_leaves_old_file_as_orphan_removed_by_sweep(self, tmp_path, user_profile):
        _, profile = user_profile
        animal = Animal.objects.create(full_name="Rex", owner=profile)
        animal.profile_image.save("old.png", ContentFile(b"fake"), save=True)
        old_path = Path(animal.profile_image.path)
        assert old_path.exists()

        # Replace never deletes the previous physical file — the sweep is expected to catch it.
        animal.profile_image.save("new.png", ContentFile(b"fake"), save=True)
        new_name = _basename(animal.profile_image.name)

        self._run()

        assert not old_path.exists()
        assert (tmp_path / "profile_pics" / "animals" / new_name).exists()
