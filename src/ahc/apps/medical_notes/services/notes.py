"""Services for MedicalRecord creation and update."""

from __future__ import annotations

from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord


def create_note(author_profile, animal, form) -> MedicalRecord:
    """Create and persist a MedicalRecord from a validated form.

    Sets the animal and author before saving. Handles M2M relationships
    (additional_animals) via save_m2m().
    """
    note = form.save(commit=False)
    note.animal = animal
    note.author = author_profile
    note.save()
    form.save_m2m()
    return note


def next_route_for(note: MedicalRecord, animal_id) -> tuple[str, dict]:
    """Return the (url_name, kwargs) pair describing where to redirect after note creation.

    The caller is responsible for performing the redirect.
    """
    event = note.type_of_event
    if event == "biometric_record":
        return "biometric_create", {"pk": animal_id, "note_id": note.id}
    if event == "diet_note":
        return "feeding_create", {"pk": note.id}
    return "full_timeline_of_notes", {"pk": animal_id}


def update_note(note: MedicalRecord, form) -> MedicalRecord:
    """Apply form data to an existing MedicalRecord and save."""
    if "animal" in form.cleaned_data:
        note.animal = form.cleaned_data["animal"]
    note.save()
    note.additional_animals.set(form.cleaned_data.get("additional_animals") or [])
    return note
