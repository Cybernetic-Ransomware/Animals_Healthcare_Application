"""Permission mixins for medical_notes views.

Each mixin implements test_func by delegating to a selector from
ahc.apps.medical_notes.selectors, keeping views free of inline permission logic.

Two access-level patterns exist:
- AnimalDirectAccessRequiredMixin — pk in URL is an Animal UUID directly.
- AnimalAccessRequiredMixin — pk in URL is a MedicalRecord UUID; access is
  checked on the linked animal.
- NoteAuthorRequiredMixin — pk is a MedicalRecord UUID; author-only access.
- AttachmentAuthorRequiredMixin — pk is a MedicalRecordAttachment UUID.
"""

from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import get_object_or_404

from ahc.apps.animals.models import Animal
from ahc.apps.animals.selectors import user_can_access_animal
from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord, MedicalRecordAttachment
from ahc.apps.medical_notes.selectors import (
    can_access_note_animal,
    is_attachment_author,
    is_note_author,
)


class AnimalDirectAccessRequiredMixin(UserPassesTestMixin):
    """Allow access when pk in URL is an Animal UUID and the profile can access it."""

    def test_func(self):
        animal = get_object_or_404(Animal, id=self.kwargs.get("pk"))
        return user_can_access_animal(self.request.user.profile, animal)


class AnimalAccessRequiredMixin(UserPassesTestMixin):
    """Allow access when pk in URL is a MedicalRecord UUID and the profile can access its animal."""

    def test_func(self):
        note = get_object_or_404(MedicalRecord, id=self.kwargs.get("pk"))
        return can_access_note_animal(self.request.user.profile, note)


class NoteAuthorRequiredMixin(UserPassesTestMixin):
    """Allow access only to the author of the MedicalRecord (pk = note UUID)."""

    def test_func(self):
        note = get_object_or_404(MedicalRecord, id=self.kwargs.get("pk"))
        return is_note_author(self.request.user.profile, note)


class AttachmentAuthorRequiredMixin(UserPassesTestMixin):
    """Allow access only to the author of the note that owns the attachment (pk = attachment UUID)."""

    def test_func(self):
        attachment = get_object_or_404(MedicalRecordAttachment, pk=self.kwargs.get("pk"))
        return is_attachment_author(self.request.user.profile, attachment)
