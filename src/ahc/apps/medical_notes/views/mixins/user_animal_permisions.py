"""Permission mixins for medical_notes views.

Each mixin implements test_func by delegating to a selector from
ahc.apps.medical_notes.selectors, keeping views free of inline permission logic.

Five access-level patterns exist:
- AnimalDirectViewMixin — pk in URL is an Animal UUID; grants read-only access
  (owner always; carer only if living animal + active share).
- AnimalDirectModifyMixin — pk in URL is an Animal UUID; grants write access
  (blocked entirely on deceased animals, even for the owner).
- BiometricModifyMixin — pk in URL is an Animal UUID; grants biometric write access
  (owner always; carer needs allow_biometrics=True on their active share).
- AnimalAccessRequiredMixin — pk in URL is a MedicalRecord UUID; write access
  checked on the linked animal via can_access_note_animal.
- NoteAuthorRequiredMixin — pk is a MedicalRecord UUID; author-only access.
- AttachmentAuthorRequiredMixin — pk is a MedicalRecordAttachment UUID.

AnimalDirectAccessRequiredMixin is kept as a backward-compatible alias for
AnimalDirectViewMixin; prefer the explicit names in new code.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import get_object_or_404

from ahc.apps.animals.models import Animal
from ahc.apps.animals.selectors import user_can_modify_animal, user_can_record_biometrics, user_can_view_animal
from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord, MedicalRecordAttachment
from ahc.apps.medical_notes.selectors import (
    can_access_note_animal,
    is_attachment_author,
    is_note_author,
)

if TYPE_CHECKING:
    from ahc.types import AuthenticatedRequest


class AnimalDirectViewMixin(UserPassesTestMixin):
    """Allow read access when pk in URL is an Animal UUID.

    The owner may always view (including deceased animals in read-only mode).
    Carers are blocked on deceased animals.
    """

    request: AuthenticatedRequest

    def test_func(self):
        animal = get_object_or_404(Animal, id=self.kwargs.get("pk"))
        return user_can_view_animal(self.request.user.profile, animal)


class AnimalDirectModifyMixin(UserPassesTestMixin):
    """Allow write access when pk in URL is an Animal UUID.

    Deceased animals are blocked for everyone — including the owner.
    """

    request: AuthenticatedRequest

    def test_func(self):
        animal = get_object_or_404(Animal, id=self.kwargs.get("pk"))
        return user_can_modify_animal(self.request.user.profile, animal)


# Backward-compatible alias — existing views that only need read access continue to work.
AnimalDirectAccessRequiredMixin = AnimalDirectViewMixin


class BiometricModifyMixin(UserPassesTestMixin):
    """Allow biometric writes when pk is an Animal UUID and the profile may record biometrics.

    Owners always pass; carers need allow_biometrics=True on their active share.
    Deceased animals are blocked for everyone (user_can_record_biometrics delegates to
    user_can_modify_animal which enforces that invariant).
    """

    request: AuthenticatedRequest

    def test_func(self):
        animal = get_object_or_404(Animal, id=self.kwargs.get("pk"))
        return user_can_record_biometrics(self.request.user.profile, animal)


class AnimalAccessRequiredMixin(UserPassesTestMixin):
    """Allow write access when pk in URL is a MedicalRecord UUID and the profile may write to its animal."""

    request: AuthenticatedRequest

    def test_func(self):
        note = get_object_or_404(MedicalRecord, id=self.kwargs.get("pk"))
        return can_access_note_animal(self.request.user.profile, note)


class NoteAuthorRequiredMixin(UserPassesTestMixin):
    """Allow access only to the author of the MedicalRecord (pk = note UUID)."""

    request: AuthenticatedRequest

    def test_func(self):
        note = get_object_or_404(MedicalRecord, id=self.kwargs.get("pk"))
        return is_note_author(self.request.user.profile, note)


class AttachmentAuthorRequiredMixin(UserPassesTestMixin):
    """Allow access only to the author of the note that owns the attachment (pk = attachment UUID)."""

    request: AuthenticatedRequest

    def test_func(self):
        attachment = get_object_or_404(MedicalRecordAttachment, pk=self.kwargs.get("pk"))
        return is_attachment_author(self.request.user.profile, attachment)
