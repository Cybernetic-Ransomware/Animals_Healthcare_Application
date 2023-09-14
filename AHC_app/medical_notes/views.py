from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import models
from django.shortcuts import get_object_or_404
from django.views.generic.edit import FormView

from animals.models import Animal as AnimalProfile
from .models import MedicalRecord
from .forms import MedicalRecordForm


class CreateNoteFormView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = 'medical_notes/create.html'
    form_class = MedicalRecordForm
    success_url = "/pet/animals/"

    def form_valid(self, form):
        animal_id = self.kwargs.get('pk')
        animal = get_object_or_404(AnimalProfile, id=animal_id)

        new_note = form.save(commit=False)
        new_note.animal = animal
        new_note.save()

        form.save()

        return super().form_valid(form)

    def test_func(self):
        user = self.request.user.profile

        animal_id = self.kwargs.get('pk')
        animal = get_object_or_404(AnimalProfile, id=animal_id)

        all_users = set(animal.allowed_users.all())
        all_users.add(animal.owner)

        return user in all_users
