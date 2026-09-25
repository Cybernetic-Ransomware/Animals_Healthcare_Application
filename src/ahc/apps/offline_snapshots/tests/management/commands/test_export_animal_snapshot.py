import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.integration
class TestExportCommand:
    def test_exports_as_owner_by_default(self, snapshot_animal, tmp_path):
        animal, _ = snapshot_animal

        call_command("export_animal_snapshot", str(animal.id), "--output-dir", str(tmp_path))

        assert (tmp_path / f"animal_{animal.id}.db").exists()

    def test_unknown_animal_raises_command_error(self, db, tmp_path):
        with pytest.raises(CommandError, match="No animal found"):
            call_command("export_animal_snapshot", "not-a-uuid", "--output-dir", str(tmp_path))

    def test_unknown_username_raises_command_error(self, snapshot_animal, tmp_path):
        animal, _ = snapshot_animal

        with pytest.raises(CommandError, match="No profile found"):
            call_command("export_animal_snapshot", str(animal.id), "--username", "ghost", "--output-dir", str(tmp_path))

    def test_denied_profile_raises_command_error(self, snapshot_animal, second_user_profile, tmp_path):
        animal, _ = snapshot_animal
        user, _ = second_user_profile

        with pytest.raises(CommandError, match="no access"):
            call_command(
                "export_animal_snapshot", str(animal.id), "--username", user.username, "--output-dir", str(tmp_path)
            )
