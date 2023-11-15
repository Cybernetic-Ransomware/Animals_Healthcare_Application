from animals.models import Animal as AnimalProfile
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, reverse
from django.views.generic.edit import FormView, UpdateView
from django.views.generic.list import ListView
from medical_notes.forms.type_feeding_notes import (
    DietRecordForm,
    NotificationRecordForm,
)
from medical_notes.models.type_basic_note import MedicalRecord
from medical_notes.models.type_feeding_notes import EmailNotification, FeedingNote


class DietRecordCreateView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = "medical_notes/create.html"
    form_class = DietRecordForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_name"] = str(self.form_class.__name__)
        return context

    def form_valid(self, form):
        print("Validating form")
        note_id = self.kwargs.get("pk")
        print("")

        related_note = get_object_or_404(MedicalRecord, id=note_id)
        animal = get_object_or_404(AnimalProfile, id=related_note.id)

        feeding_note = form.save(commit=False)
        feeding_note.related_note = related_note
        feeding_note.save()

        success_url = reverse("animal_profile", kwargs={"pk": animal.id})
        return redirect(success_url)

    def test_func(self):
        user = self.request.user.profile

        note_id = self.kwargs.get("pk")
        related_note = get_object_or_404(MedicalRecord, id=note_id)
        animal = get_object_or_404(AnimalProfile, id=related_note.animal.id)

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
        note_id = self.kwargs.get("pk")
        return get_object_or_404(FeedingNote, related_note__id=note_id)

    def form_valid(self, form):
        return super().form_valid(form)

    def get_success_url(self):
        note_id = self.kwargs.get("pk")
        note = get_object_or_404(MedicalRecord, pk=note_id)
        animal_id = note.animal.id
        return reverse("full_timeline_of_notes", kwargs={"pk": animal_id})

    def test_func(self):
        user = self.request.user.profile

        note_id = self.kwargs.get("pk")
        note_author = get_object_or_404(MedicalRecord, id=note_id).author
        return user == note_author


class FeedingNoteListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = FeedingNote
    template_name = "medical_notes/feeding_notes_list.html"
    context_object_name = "feeding_notes"

    def get_queryset(self):
        record_id = self.kwargs.get("pk")
        print(f"{record_id=}")

        medical_record = get_object_or_404(MedicalRecord, pk=record_id)
        print(f"{medical_record.id=}")
        queryset = FeedingNote.objects.filter(related_note=medical_record.id)
        print(f"{queryset=}")
        id("dupa1")

        # medical_record_id = FeedingNote.objects.filter(id=record_id).first().id
        # queryset = FeedingNote.objects.filter(related_notes__id=medical_record_id)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['medical_record_id'] = self.kwargs['pk']
        return context

    def test_func(self):
        return True


class CreateNotificationView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = "medical_notes/create_notify.html"
    form_class = NotificationRecordForm
    success_url = "/"  # -> manage notifications

    def get_object(self):
        note_id = self.kwargs.get("pk")
        return get_object_or_404(FeedingNote, id=note_id)

    def form_valid(self, form):
        note_id = self.kwargs.get("pk")
        related_note = get_object_or_404(FeedingNote, id=note_id)

        notify = form.save(commit=False)
        days_of_week = [int(day) for day in self.request.POST.getlist("days_of_week")]

        processed_days_of_week = [False] * 7
        for i in days_of_week:
            processed_days_of_week[i] = True

        notify.related_note = related_note
        notify.days_of_week = processed_days_of_week
        notify.save()

        return super().form_valid(form)

    def test_func(self):
        return True


class NotificationListView(ListView):
    template_name = "medical_notes/notification_list.html"  # Szablon do wyrenderowania listy notyfikacji
    context_object_name = "notifications"

    def get_queryset(self):
        medical_record_pk = self.kwargs.get("pk")
        print(f"{medical_record_pk=}")
        medical_record = MedicalRecord.objects.get(pk=medical_record_pk)
        print(f"{medical_record=}")

        feeding_notes = FeedingNote.objects.filter(related_note=medical_record).all()
        print(f"{feeding_notes=}")

        notifications = []
        for feeding_note in feeding_notes:
            print(f"{feeding_note.pk=}")
            email_notifications = EmailNotification.objects.filter(
                related_note=feeding_note
            ).all()
            # sms_notifications = SMSNotification.objects.filter(related_note__in=feeding_notes)
            # discord_notifications = DiscordNotification.objects.filter(related_note__in=feeding_notes)
            #
            # notifications.extend(list(email_notifications) + list(sms_notifications) + list(discord_notifications))
            notifications.extend(email_notifications)
        print(f"{notifications=}")
        return notifications
