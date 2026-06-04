from django.apps import AppConfig


class MedicalNotesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ahc.apps.medical_notes"

    def ready(self):
        from . import signals  # noqa: F401
