from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic.edit import FormView

from ahc.apps.animals.models import Animal as AnimalProfile
from ahc.apps.animals.selectors import animals_for_biometric_batch
from ahc.apps.medical_notes.forms.biometric_batch import BiometricBatchFormSet, BiometricBatchSessionForm
from ahc.apps.medical_notes.forms.type_measurement_notes import BiometricRecordForm
from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
from ahc.apps.medical_notes.services.biometrics import create_batch_biometric_records, create_biometric_record
from ahc.apps.medical_notes.views.mixins.user_animal_permisions import BiometricModifyMixin

if TYPE_CHECKING:
    from ahc.types import AuthenticatedRequest


class BiometricRecordCreateView(LoginRequiredMixin, BiometricModifyMixin, FormView):
    template_name = "medical_notes/create.html"
    form_class = BiometricRecordForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_name"] = str(self.form_class.__name__)
        return context

    def form_valid(self, form):
        animal_id = self.kwargs.get("pk")
        note_id = self.kwargs.get("note_id")

        animal = get_object_or_404(AnimalProfile, id=animal_id)
        related_note = get_object_or_404(MedicalRecord, id=note_id)

        create_biometric_record(
            animal=animal,
            related_note=related_note,
            record_type=form.cleaned_data["record_type"],
            data=form.cleaned_data,
        )

        return redirect(reverse("animal_profile", kwargs={"pk": animal_id}))


class BiometricBatchCreateView(LoginRequiredMixin, View):
    """Full-page form for entering one measurement type for multiple animals at once.

    A single POST creates one MedicalRecord + BiometricRecord pair per checked row.
    The session form controls the record type and unit; the formset has one row per
    animal accessible to the current user.
    """

    template_name = "medical_notes/biometric_batch.html"
    request: AuthenticatedRequest

    def _build_context(self, session_form, formset, animals):
        return {
            "session_form": session_form,
            "formset": formset,
            "rows": list(zip(formset.forms, animals, strict=False)),
        }

    def get(self, request, *args, **kwargs):
        animals = list(animals_for_biometric_batch(request.user.profile))
        session_form = BiometricBatchSessionForm()
        formset = BiometricBatchFormSet(initial=[{"animal_id": a.id} for a in animals])
        return render(request, self.template_name, self._build_context(session_form, formset, animals))

    def post(self, request, *args, **kwargs):
        animals = list(animals_for_biometric_batch(request.user.profile))
        session_form = BiometricBatchSessionForm(request.POST)
        formset = BiometricBatchFormSet(request.POST)

        if not (session_form.is_valid() and formset.is_valid()):
            return render(request, self.template_name, self._build_context(session_form, formset, animals))

        profile = request.user.profile
        allowed = {a.id: a for a in animals}
        record_type = session_form.cleaned_data["record_type"]
        unit = session_form.cleaned_data.get("unit") or ""
        custom_name = session_form.cleaned_data.get("custom_name", "")
        custom_unit = session_form.cleaned_data.get("custom_unit", "")

        rows = []
        for form in formset.forms:
            if not form.cleaned_data.get("include"):
                continue
            animal_id = form.cleaned_data["animal_id"]
            if animal_id not in allowed:
                continue
            value = form.cleaned_data["value"]
            if record_type == "weight":
                data_dict = {"weight": value, "weight_unit_to_present": unit or "g"}
            elif record_type == "height":
                data_dict = {"height": value, "height_unit_to_present": unit or "mm"}
            else:
                data_dict = {"custom_name": custom_name, "custom_value": str(value), "custom_unit": custom_unit}
            rows.append((allowed[animal_id], data_dict))

        n = create_batch_biometric_records(
            author_profile=profile,
            record_type=record_type,
            rows=rows,
            allowed_ids=set(allowed.keys()),
        )
        messages.success(request, f"Saved {n} measurement(s).")
        return redirect(reverse("biometric_batch"))
