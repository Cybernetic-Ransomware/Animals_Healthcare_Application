from animals.models import Animal as AnimalProfile
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, reverse
from django.urls import reverse_lazy
from django.views.generic.edit import FormView, UpdateView
from django.views.generic.list import ListView
from medical_notes.forms.type_feeding_notes import (
    DietRecordForm,
    NotificationRecordForm
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
        note_id = self.kwargs.get("pk")

        related_note = get_object_or_404(MedicalRecord, id=note_id)
        animal = related_note.animal

        feeding_note = form.save(commit=False)
        feeding_note.related_note = related_note
        feeding_note.save()

        success_url = reverse("note_related_diets", kwargs={"pk": note_id})
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
    template_name = "medical_notes/edit.html"
    form_class = DietRecordForm
    context_object_name = "note"

    def get_context_data(self, **kwargs):
        from icecream import ic

        ic("dupa1")
        context = super().get_context_data(**kwargs)
        context["form_name"] = str(self.form_class.__name__)
        return context

    def form_valid(self, form):
        # note_id = self.kwargs.get("pk")
        # related_note = get_object_or_404(FeedingNote, related_note__id=note_id)

        # feeding_note = form.save(commit=False)
        # feeding_note.related_note = related_note
        # feeding_note.save()
        feeding_note = form.save(commit=True)

        # success_url = reverse_lazy("note_related_diets", kwargs={"pk": note_id})
        email_notification_id = self.kwargs.get("pk")
        email_notification = get_object_or_404(
            EmailNotification, id=email_notification_id
        )
        feeding_note = email_notification.related_note
        medical_record = feeding_note.related_note

        success_url = reverse_lazy(
            "note_related_diets", kwargs={"pk": medical_record.id}
        )
        return redirect(success_url)

    def get_success_url(self):
        from icecream import ic

        ic("dupa3")
        note_id = self.kwargs.get("pk")
        note = get_object_or_404(MedicalRecord, pk=note_id)
        animal_id = note.animal.id
        return reverse("full_timeline_of_notes", kwargs={"pk": animal_id})

    def test_func(self):
        from icecream import ic

        ic("dupa4")
        return True
        # user = self.request.user.profile
        #
        # note_id = self.kwargs.get("pk")
        # note_author = get_object_or_404(MedicalRecord, id=note_id).author
        # return user == note_author


class FeedingNoteListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = FeedingNote
    template_name = "medical_notes/feeding_notes_list.html"
    context_object_name = "feeding_notes"

    def get_queryset(self):
        record_id = self.kwargs.get("pk")
        medical_record = get_object_or_404(MedicalRecord, pk=record_id)
        queryset = FeedingNote.objects.filter(related_note=medical_record.id)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["medical_record_id"] = self.kwargs.get("pk")
        context["animal_id"] = get_object_or_404(
            MedicalRecord, pk=self.kwargs.get("pk")
        ).animal.id
        return context

    def test_func(self):
        return True


class CreateNotificationView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = "medical_notes/create_notify.html"
    form_class = NotificationRecordForm
    success_url = "/"

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

        notify.days_of_week = processed_days_of_week
        notify.related_note = related_note

        notify_kwargs = {key: value for key, value in notify.__dict__.items() if not key.startswith('_')}
        print(notify_kwargs)

        EmailNotification.objects.create_notification(
            **notify_kwargs

        )

        return super().form_valid(form)

    def test_func(self):
        return True


class NotificationListView(ListView):
    template_name = "medical_notes/notification_list.html"
    context_object_name = "notifications"

    def get_queryset(self):
        feednote_pk = self.request.GET.get("feednote_pk")
        mednote_uuid = self.request.GET.get("mednote_uuid")
        animal_uuid = self.request.GET.get("animal_uuid")

        if feednote_pk:
            email_notifications = EmailNotification.objects.filter(
                related_note=feednote_pk
            )
            flattened_email_notifications = list(email_notifications)

            return flattened_email_notifications

        elif mednote_uuid:
            pass

        elif animal_uuid:
            pass

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["feednote_pk"] = self.request.GET.get("feednote_pk")
        context["mednote_uuid"] = self.request.GET.get("mednote_uuid")
        context["animal_uuid"] = self.request.GET.get("animal_uuid")
        return context

    def post(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        notify = get_object_or_404(EmailNotification, pk=pk)

        notify.is_active = not notify.is_active
        notify.save()

        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    def delete(self, *args, **kwargs):
        pk = kwargs.get('pk')
        notify = get_object_or_404(self.model, pk=pk)
        notify.delete()

        return HttpResponseRedirect(reverse_lazy('note_related_notifications'))
