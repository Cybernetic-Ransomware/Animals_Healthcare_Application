from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic.edit import FormView, UpdateView
from django.views.generic.list import ListView

from ahc.apps.medical_notes.forms.type_feeding_notes import (
    DietRecordForm,
    NotificationRecordForm,
)
from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
from ahc.apps.medical_notes.models.type_feeding_notes import EmailNotification, FeedingNote
from ahc.apps.medical_notes.selectors import (
    feeding_notes_for,
    is_note_author,
    notifications_for_feednote,
    notifications_for_mednote,
)
from ahc.apps.medical_notes.services.feeding import create_feeding_note
from ahc.apps.medical_notes.services.notifications import (
    create_email_notification,
    delete_notification,
    toggle_notification,
)
from ahc.apps.medical_notes.views.mixins.user_animal_permisions import AnimalAccessRequiredMixin

if TYPE_CHECKING:
    from ahc.types import AuthenticatedRequest


class DietRecordCreateView(LoginRequiredMixin, AnimalAccessRequiredMixin, FormView):
    template_name = "medical_notes/create.html"
    form_class = DietRecordForm
    request: AuthenticatedRequest

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_name"] = str(self.form_class.__name__)
        return context

    def form_valid(self, form):
        note_id = self.kwargs.get("pk")
        related_note = get_object_or_404(MedicalRecord, id=note_id)
        create_feeding_note(related_note, form)
        return redirect(reverse("note_related_diets", kwargs={"pk": note_id}))


class EditDietRecordView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = FeedingNote
    template_name = "medical_notes/edit.html"
    form_class = DietRecordForm
    context_object_name = "note"
    request: AuthenticatedRequest

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_name"] = str(self.form_class.__name__)
        return context

    def get_success_url(self):
        return reverse("note_related_diets", kwargs={"pk": self.object.related_note.id})

    def test_func(self):
        feeding_note = get_object_or_404(FeedingNote, id=self.kwargs.get("pk"))
        return is_note_author(self.request.user.profile, feeding_note.related_note)


class FeedingNoteListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = FeedingNote
    template_name = "medical_notes/feeding_notes_list.html"
    context_object_name = "feeding_notes"
    request: AuthenticatedRequest

    def get_queryset(self):
        medical_record = get_object_or_404(MedicalRecord, pk=self.kwargs.get("pk"))
        return feeding_notes_for(medical_record)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["medical_record_id"] = self.kwargs.get("pk")
        context["animal_id"] = get_object_or_404(MedicalRecord, pk=self.kwargs.get("pk")).animal.id
        return context

    def test_func(self):
        note = get_object_or_404(MedicalRecord, id=self.kwargs.get("pk"))
        return is_note_author(self.request.user.profile, note)


class CreateNotificationView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = "medical_notes/create.html"
    form_class = NotificationRecordForm
    success_url = "/"
    request: AuthenticatedRequest

    def get_object(self):
        return get_object_or_404(FeedingNote, id=self.kwargs.get("pk"))

    def form_valid(self, form):
        related_note = get_object_or_404(FeedingNote, id=self.kwargs.get("pk"))
        notify = form.save(commit=False)
        create_email_notification(
            related_note=related_note,
            form_instance=notify,
            days_of_week_raw=self.request.POST.getlist("days_of_week"),
        )
        return super().form_valid(form)

    def test_func(self):
        feeding_note = get_object_or_404(FeedingNote, id=self.kwargs.get("pk"))
        from ahc.apps.medical_notes.selectors import can_access_note_animal

        return can_access_note_animal(self.request.user.profile, feeding_note.related_note)


class NotificationListView(LoginRequiredMixin, ListView):
    template_name = "medical_notes/notification_list.html"
    context_object_name = "notifications"

    def get_queryset(self):
        feednote_pk = self.request.GET.get("feednote_pk")
        mednote_uuid = self.request.GET.get("mednote_uuid")

        if feednote_pk:
            return list(notifications_for_feednote(feednote_pk))
        if mednote_uuid:
            return notifications_for_mednote(mednote_uuid)
        return EmailNotification.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["feednote_pk"] = self.request.GET.get("feednote_pk")
        context["mednote_uuid"] = self.request.GET.get("mednote_uuid")
        context["animal_uuid"] = self.request.GET.get("animal_uuid")
        return context

    def post(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        toggle_notification(pk)
        return HttpResponseRedirect(request.META.get("HTTP_REFERER"))

    def delete(self, *args, **kwargs):
        pk = kwargs.get("pk")
        delete_notification(pk)
        return HttpResponseRedirect(reverse_lazy("note_related_notifications"))
