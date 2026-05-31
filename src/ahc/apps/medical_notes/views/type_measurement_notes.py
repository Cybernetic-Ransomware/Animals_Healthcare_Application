from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic.edit import FormView

from ahc.apps.animals.models import Animal as AnimalProfile
from ahc.apps.medical_notes.forms.type_measurement_notes import BiometricRecordForm
from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
from ahc.apps.medical_notes.services.biometrics import create_biometric_record
from ahc.apps.medical_notes.views.mixins.user_animal_permisions import AnimalDirectAccessRequiredMixin


class BiometricRecordCreateView(LoginRequiredMixin, AnimalDirectAccessRequiredMixin, FormView):
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
