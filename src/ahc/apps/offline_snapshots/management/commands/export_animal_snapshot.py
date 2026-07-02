from pathlib import Path

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management.base import BaseCommand, CommandError

from ahc.apps.animals.models import Animal
from ahc.apps.animals.selectors import profile_by_username
from ahc.apps.offline_snapshots.services.exporter import export_animal_snapshot


class Command(BaseCommand):
    help = "Export a read-only SQLite snapshot of one animal's health data (see ADR-12)."

    def add_arguments(self, parser):
        parser.add_argument("animal_id", help="UUID of the animal to export")
        parser.add_argument("--output-dir", default="exports", help="Directory for the snapshot file (default: exports)")
        parser.add_argument("--username", default=None, help="Export as this user (default: the animal's owner)")
        parser.add_argument("--force", action="store_true", help="Rebuild the snapshot if the file already exists")

    def handle(self, *args, **options):
        try:
            animal = Animal.objects.get(pk=options["animal_id"])
        except (Animal.DoesNotExist, ValidationError, ValueError) as exc:
            raise CommandError(f"No animal found for id '{options['animal_id']}'.") from exc

        if options["username"]:
            profile = profile_by_username(options["username"])
            if profile is None:
                raise CommandError(f"No profile found for username '{options['username']}'.")
        else:
            profile = animal.owner
            if profile is None:
                raise CommandError("Animal has no owner; pass --username to export as a specific user.")

        try:
            path = export_animal_snapshot(animal, profile, Path(options["output_dir"]), force=options["force"])
        except PermissionDenied as exc:
            raise CommandError(str(exc)) from exc
        except FileExistsError as exc:
            raise CommandError(f"{exc} (use --force to rebuild)") from exc

        self.stdout.write(self.style.SUCCESS(f"Snapshot written to {path}"))
