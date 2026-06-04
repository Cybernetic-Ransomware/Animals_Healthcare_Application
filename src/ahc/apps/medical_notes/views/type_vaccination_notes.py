"""Views for inline CRUD of VaccinationNote records.

All views return HTML fragments (partial <tr> elements) consumed by htmx
on the Vaccinations tab.  Each view redirects to the Vaccinations tab when
accessed without the HX-Request header (progressive-enhancement fallback).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import View

from ahc.apps.animals.models import Animal
from ahc.apps.animals.selectors import allowed_categories_for, is_animal_owner, user_can_modify_animal

if TYPE_CHECKING:
    from ahc.types import AuthenticatedRequest
from ahc.apps.medical_notes.forms.type_vaccination_notes import VaccinationNoteForm
from ahc.apps.medical_notes.models.type_vaccination_notes import VaccinationNote
from ahc.apps.medical_notes.services.vaccinations import (
    create_vaccination_note,
    delete_vaccination_note,
    update_vaccination_note,
)


def _has_vaccination_access(profile, animal: Animal) -> bool:
    """Return True if profile may write (add/edit/delete) vaccinations on this animal.

    Uses user_can_modify_animal so deceased animals are blocked for everyone,
    including the owner.
    """
    if not user_can_modify_animal(profile, animal):
        return False
    if is_animal_owner(profile, animal):
        return True
    allowed = allowed_categories_for(profile, animal)
    return "vaccinations" in allowed


def _vaccinations_tab_url(animal_id) -> str:
    return reverse("animal_tab", kwargs={"pk": animal_id, "slug": "vaccinations"})


class VaccinationAnimalAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Access check for views where pk in URL is an Animal UUID."""

    request: AuthenticatedRequest

    def test_func(self) -> bool:
        animal = get_object_or_404(Animal, id=self.kwargs["pk"])  # type: ignore
        return _has_vaccination_access(self.request.user.profile, animal)


class VaccinationRecordAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Access check for views where vacc_id in URL is a VaccinationNote UUID."""

    request: AuthenticatedRequest

    def _get_vaccination(self) -> VaccinationNote:
        return get_object_or_404(VaccinationNote, id=self.kwargs["vacc_id"])  # type: ignore

    def test_func(self) -> bool:
        vaccination = self._get_vaccination()
        animal = vaccination.related_note.animal
        return _has_vaccination_access(self.request.user.profile, animal)


class VaccinationAddView(VaccinationAnimalAccessMixin, View):
    """GET: render empty editable row. POST: create record, return read-only row."""

    def get(self, request, pk):
        form = VaccinationNoteForm()
        return HttpResponse(_render_form_row(request, form, animal_id=pk, is_new=True))

    def post(self, request, pk):
        animal = get_object_or_404(Animal, id=pk)
        form = VaccinationNoteForm(request.POST)
        if form.is_valid():
            vaccination = create_vaccination_note(request.user.profile, animal, form)
            return HttpResponse(_render_readonly_row(request, vaccination))
        return HttpResponse(
            _render_form_row(request, form, animal_id=pk, is_new=True),
            status=422,
        )


class VaccinationEditView(VaccinationRecordAccessMixin, View):
    """GET: return editable row populated with current values."""

    def get(self, request, vacc_id):
        vaccination = self._get_vaccination()
        form = VaccinationNoteForm(instance=vaccination)
        return HttpResponse(_render_form_row(request, form, vaccination=vaccination, is_new=False))


class VaccinationSaveView(VaccinationRecordAccessMixin, View):
    """POST: save changes to an existing VaccinationNote, return read-only row."""

    def post(self, request, vacc_id):
        vaccination = self._get_vaccination()
        form = VaccinationNoteForm(request.POST, instance=vaccination)
        if form.is_valid():
            vaccination = update_vaccination_note(vaccination, form)
            return HttpResponse(_render_readonly_row(request, vaccination))
        return HttpResponse(
            _render_form_row(request, form, vaccination=vaccination, is_new=False),
            status=422,
        )


class VaccinationCancelView(VaccinationRecordAccessMixin, View):
    """GET: discard edits, return read-only row (no DB change)."""

    def get(self, request, vacc_id):
        vaccination = self._get_vaccination()
        return HttpResponse(_render_readonly_row(request, vaccination))


class VaccinationDeleteView(VaccinationRecordAccessMixin, View):
    """POST: delete record, return empty response so htmx removes the row."""

    def post(self, request, vacc_id):
        vaccination = self._get_vaccination()
        delete_vaccination_note(vaccination)
        return HttpResponse("")


def _render_readonly_row(request, vaccination: VaccinationNote) -> str:
    from django.template.loader import render_to_string

    return render_to_string(
        "medical_notes/partials/_vaccination_row.html",
        {"vaccination": vaccination},
        request=request,
    )


def _render_form_row(request, form, animal_id=None, vaccination: VaccinationNote | None = None, is_new: bool = True) -> str:
    from django.template.loader import render_to_string

    return render_to_string(
        "medical_notes/partials/_vaccination_row_form.html",
        {
            "form": form,
            "animal_id": animal_id,
            "vaccination": vaccination,
            "is_new": is_new,
        },
        request=request,
    )
