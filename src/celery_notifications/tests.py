import os
import shutil
import time
from datetime import timedelta
from pathlib import Path

import pytest
from django.core.files.base import ContentFile

from ahc.apps.animals.models import Animal
from celery_notifications.cron import ORPHAN_IMAGE_GRACE_PERIOD, _clean_orphaned_images, clean_orphaned_profile_images


def _basename(field_name: str | None) -> str:
    assert field_name is not None
    return Path(field_name).name


def _backdate(path: Path, age: timedelta = ORPHAN_IMAGE_GRACE_PERIOD + timedelta(hours=1)) -> None:
    """Push a file's mtime past ORPHAN_IMAGE_GRACE_PERIOD without sleeping."""
    old = time.time() - age.total_seconds()
    os.utime(path, (old, old))


@pytest.mark.unit
class TestCleanOrphanedImagesHelper:
    """_clean_orphaned_images: pure filesystem helper, no DB."""

    def test_orphan_file_removed(self, tmp_path):
        orphan = tmp_path / "orphan.png"
        orphan.write_bytes(b"x")
        _backdate(orphan)

        removed, failed = _clean_orphaned_images(tmp_path, live_names=set())

        assert (removed, failed) == (1, 0)
        assert not orphan.exists()

    def test_live_file_kept(self, tmp_path):
        (tmp_path / "live.png").write_bytes(b"x")

        removed, failed = _clean_orphaned_images(tmp_path, live_names={"live.png"})

        assert (removed, failed) == (0, 0)
        assert (tmp_path / "live.png").exists()

    def test_missing_directory_is_a_no_op(self, tmp_path):
        missing = tmp_path / "does-not-exist"

        assert _clean_orphaned_images(missing, live_names=set()) == (0, 0)

    def test_unexpected_subdirectory_is_skipped_not_deleted(self, tmp_path):
        orphan = tmp_path / "orphan.png"
        orphan.write_bytes(b"x")
        _backdate(orphan)
        (tmp_path / "stray-subdir").mkdir()
        (tmp_path / "stray-subdir" / "nested.png").write_bytes(b"x")

        removed, failed = _clean_orphaned_images(tmp_path, live_names=set())

        assert (removed, failed) == (1, 0)
        assert not orphan.exists()
        assert (tmp_path / "stray-subdir").is_dir()

    def test_mixed_live_and_orphan_files(self, tmp_path):
        (tmp_path / "live.png").write_bytes(b"x")
        orphan1 = tmp_path / "orphan1.png"
        orphan2 = tmp_path / "orphan2.png"
        orphan1.write_bytes(b"x")
        orphan2.write_bytes(b"x")
        _backdate(orphan1)
        _backdate(orphan2)

        removed, failed = _clean_orphaned_images(tmp_path, live_names={"live.png"})

        assert (removed, failed) == (2, 0)
        assert (tmp_path / "live.png").exists()
        assert not orphan1.exists()
        assert not orphan2.exists()

    def test_fresh_orphan_within_grace_period_is_kept(self, tmp_path):
        fresh = tmp_path / "fresh.png"
        fresh.write_bytes(b"x")  # mtime = now, well inside ORPHAN_IMAGE_GRACE_PERIOD

        removed, failed = _clean_orphaned_images(tmp_path, live_names=set())

        assert (removed, failed) == (0, 0)
        assert fresh.exists()

    def test_old_orphan_past_grace_period_is_removed(self, tmp_path):
        old = tmp_path / "old.png"
        old.write_bytes(b"x")
        _backdate(old)

        removed, failed = _clean_orphaned_images(tmp_path, live_names=set())

        assert (removed, failed) == (1, 0)
        assert not old.exists()

    def test_unlink_failure_on_one_file_does_not_abort_the_rest(self, tmp_path, monkeypatch):
        orphan_a = tmp_path / "orphan_a.png"
        orphan_b = tmp_path / "orphan_b.png"
        orphan_a.write_bytes(b"x")
        orphan_b.write_bytes(b"x")
        _backdate(orphan_a)
        _backdate(orphan_b)

        original_unlink = Path.unlink

        def flaky_unlink(self, *args, **kwargs):
            if self.name == "orphan_a.png":
                raise PermissionError("locked")
            return original_unlink(self, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", flaky_unlink)

        removed, failed = _clean_orphaned_images(tmp_path, live_names=set())

        assert (removed, failed) == (1, 1)
        assert orphan_a.exists()
        assert not orphan_b.exists()

    def test_stat_failure_is_treated_as_skip_not_removed(self, tmp_path, monkeypatch):
        orphan = tmp_path / "orphan.png"
        orphan.write_bytes(b"x")
        _backdate(orphan)

        original_stat = Path.stat

        def flaky_stat(self, *args, **kwargs):
            if self.name == "orphan.png":
                raise OSError("stat failed")
            return original_stat(self, *args, **kwargs)

        monkeypatch.setattr(Path, "stat", flaky_stat)

        removed, failed = _clean_orphaned_images(tmp_path, live_names=set())

        assert (removed, failed) == (0, 1)
        assert orphan.exists()

    def test_directory_listdir_failure_is_reported_not_raised(self, tmp_path, monkeypatch):
        (tmp_path / "orphan.png").write_bytes(b"x")

        def flaky_listdir(path):
            raise OSError("permission denied")

        monkeypatch.setattr(os, "listdir", flaky_listdir)

        assert _clean_orphaned_images(tmp_path, live_names=set()) == (0, 0)


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
        _backdate(orphan)

        self._run()

        assert (tmp_path / "profile_pics" / "animals" / live_name).exists()
        assert not orphan.exists()

    def test_live_profile_image_kept_orphan_removed(self, tmp_path, user_profile):
        _, profile = user_profile
        profile.profile_image.save("avatar.png", ContentFile(b"fake"), save=True)
        live_name = _basename(profile.profile_image.name)

        orphan = tmp_path / "profile_pics" / "users" / "orphan.png"
        orphan.write_bytes(b"fake")
        _backdate(orphan)

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
        _backdate(old_path)

        # Replace never deletes the previous physical file — the sweep is expected to catch it.
        animal.profile_image.save("new.png", ContentFile(b"fake"), save=True)
        new_name = _basename(animal.profile_image.name)

        self._run()

        assert not old_path.exists()
        assert (tmp_path / "profile_pics" / "animals" / new_name).exists()

    def test_animals_directory_failure_does_not_block_users_sweep(self, tmp_path, user_profile, monkeypatch):
        _, profile = user_profile
        profile.profile_image.save("avatar.png", ContentFile(b"fake"), save=True)
        live_name = _basename(profile.profile_image.name)

        users_orphan = tmp_path / "profile_pics" / "users" / "orphan.png"
        users_orphan.write_bytes(b"fake")
        _backdate(users_orphan)

        animals_dir = tmp_path / "profile_pics" / "animals"
        original_listdir = os.listdir

        def flaky_listdir(path):
            if Path(path) == animals_dir:
                raise OSError("permission denied")
            return original_listdir(path)

        monkeypatch.setattr(os, "listdir", flaky_listdir)

        self._run()

        assert (tmp_path / "profile_pics" / "users" / live_name).exists()
        assert not users_orphan.exists()
