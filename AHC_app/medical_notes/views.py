from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic.edit import FormView, UpdateView, DeleteView
from django.views.generic.list import ListView

from animals.models import Animal as AnimalProfile
from .forms import MedicalRecordForm, MedicalRecordEditForm
from .models import MedicalRecord


# change animal into ManyToMany (animal -> animals), append create field for other animals, hashtags,
class CreateNoteFormView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = "medical_notes/create.html"
    form_class = MedicalRecordForm
    # success_url = "/pet/animals/"

    def form_valid(self, form):
        animal_id = self.kwargs.get("pk")
        animal = get_object_or_404(AnimalProfile, id=animal_id)

        new_note = form.save(commit=False)
        new_note.animal = animal
        new_note.save()
        form.save_m2m()

        return super().form_valid(form)

    def test_func(self):
        user = self.request.user.profile

        animal_id = self.kwargs.get("pk")
        animal = get_object_or_404(AnimalProfile, id=animal_id)

        all_users = set(animal.allowed_users.all())
        all_users.add(animal.owner)

        return user in all_users

    def get_success_url(self):
        animal_id = self.kwargs.get("pk")
        return reverse("animal_profile", kwargs={"pk": animal_id})


class FullTimelineOfNotes(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = MedicalRecord
    template_name = "medical_notes/full_timeline_of_notes.html"
    context_object_name = "notes"
    paginate_by = 4

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        animal_id = self.kwargs.get("pk")
        animal = get_object_or_404(AnimalProfile, id=animal_id)
        query = MedicalRecord.objects.filter(animal=animal).order_by("-date_creation")

        # context["notes"] = query

        paginator = Paginator(query, per_page=self.paginate_by)
        page_number = self.request.GET.get('page')
        context["notes"] = paginator.get_page(page_number)

        return context

    def test_func(self):
        user = self.request.user.profile

        animal_id = self.kwargs.get("pk")
        animal = get_object_or_404(AnimalProfile, id=animal_id)

        all_users = set(animal.allowed_users.all())
        all_users.add(animal.owner)

        return user in all_users


class TagFilteredTimelineOfNotes(FullTimelineOfNotes):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        animal_id = self.kwargs.get("pk")
        animal = get_object_or_404(AnimalProfile, id=animal_id)

        tag_name = self.kwargs.get("tag_name")
        query = MedicalRecord.objects.filter(animal=animal, note_tags__slug=tag_name).order_by("-date_creation")

        context["notes"] = query
        return context


class EditNoteView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = MedicalRecord
    form_class = MedicalRecordEditForm
    template_name = 'medical_notes/edit.html'
    context_object_name = 'note'
    success_url = "/pet/animals/"

    # to do a checkup if all connected animals (after changing to ManyToMany relationship) are under care or are ownership
    # should append author to a note
    # need to view to change animal connection from note
    def test_func(self):
        return True


class DeleteNoteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = MedicalRecord
    template_name = 'medical_notes/delete_confirm.html'
    context_object_name = 'note'
    success_url = "/pet/animals/"

    def test_func(self):
        return True
