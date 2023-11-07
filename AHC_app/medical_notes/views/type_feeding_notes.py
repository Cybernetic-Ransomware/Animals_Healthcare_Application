from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, reverse, redirect
from django.views.generic.edit import CreateView, FormView, UpdateView

from medical_notes.forms.type_feeding_notes import DietRecordForm, NotificationRecordForm
from animals.models import Animal as AnimalProfile
from medical_notes.models.type_feeding_notes import FeedingNote, EmailNotification
from medical_notes.models.type_basic_note import MedicalRecord


class DietRecordCreateView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = 'medical_notes/create.html'
    form_class = DietRecordForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_name'] = str(self.form_class.__name__)
        return context

    def form_valid(self, form):
        # animal_id = self.kwargs.get('pk')
        note_id = self.kwargs.get('note_id')

        # animal = get_object_or_404(AnimalProfile, id=animal_id)
        related_note = get_object_or_404(MedicalRecord, id=note_id)

        feeding_note = form.save(commit=False)
        feeding_note.related_note = related_note
        feeding_note.save()

        success_url = reverse("animal_profile", kwargs={"pk": animal_id})
        return redirect(success_url)

    def test_func(self):
        user = self.request.user.profile

        animal_id = self.kwargs.get("pk")
        animal = get_object_or_404(AnimalProfile, id=animal_id)

        all_users = set(animal.allowed_users.all())
        all_users.add(animal.owner)

        return user in all_users


class EditDietRecordView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = FeedingNote
    form_class = DietRecordForm
    template_name = "medical_notes/edit.html"
    context_object_name = "note"

    # def get_form_kwargs(self):
    #     kwargs = super().get_form_kwargs()
    #
    #     query = AnimalProfile.objects.filter(
    #         Q(owner=self.request.user.profile)
    #         | Q(allowed_users=self.request.user.profile)
    #     ).order_by("-creation_date")
    #
    #     animal_choices = [(animal.id, animal.full_name) for animal in query]
    #     kwargs["animal_choices"] = animal_choices
    #
    #     note_id = self.kwargs.get('pk')
    #     note = get_object_or_404(MedicalRecord, pk=note_id)
    #     animal_id = note.animal.id
    #     animal = get_object_or_404(AnimalProfile, id=animal_id)
    #     kwargs["animal"] = animal
    #     print(kwargs["animal"])
    #
    #     return kwargs
    #
    # def form_valid(self, form):
    #     note_id = self.kwargs.get("pk")
    #     note = get_object_or_404(MedicalRecord, id=note_id)
    #
    #     if "animal" in form.cleaned_data:
    #         note.animal = form.cleaned_data["animal"]
    #
    #     note.save()
    #
    #     additional_animals = form.cleaned_data.get("additional_animals")
    #     note.additional_animals.set(additional_animals)
    #
    #     return super().form_valid(form)

    def get_object(self, queryset=None):
        note_id = self.kwargs.get('pk')
        return get_object_or_404(FeedingNote, related_note__id=note_id)

    def form_valid(self, form):
        return super().form_valid(form)

    def get_success_url(self):
        note_id = self.kwargs.get('pk')
        note = get_object_or_404(MedicalRecord, pk=note_id)
        animal_id = note.animal.id
        return reverse('full_timeline_of_notes', kwargs={'pk': animal_id})

    def test_func(self):
        user = self.request.user.profile

        note_id = self.kwargs.get("pk")
        note_author = get_object_or_404(MedicalRecord, id=note_id).author
        return user == note_author


class CreateNotificationView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = 'medical_notes/create.html'
    form_class = NotificationRecordForm
    success_url = '/'  # -> manage notifications

    def get_object(self, queryset=None):
        note_id = self.kwargs.get('pk')
        return get_object_or_404(MedicalRecord, id=note_id)

    def form_valid(self, form):
        note_id = self.kwargs.get('pk')
        related_note = get_object_or_404(MedicalRecord, id=note_id)

        notify = form.save(commit=False)

        days_of_week = [False for i in range(7)]
        for i in notify.days_of_week:
            days_of_week[i] = True

        notify.related_note = related_note
        notify.days_of_week = days_of_week
        notify.save()

        return super().form_valid(form)

    def test_func(self):
        return True
