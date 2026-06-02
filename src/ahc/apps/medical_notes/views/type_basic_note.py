from datetime import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import View
from django.views.generic.edit import DeleteView, FormView, UpdateView
from django.views.generic.list import ListView

from ahc.apps.animals.models import Animal as AnimalProfile
from ahc.apps.medical_notes.forms.type_basic_note import (
    MedicalRecordEditForm,
    MedicalRecordEditRelatedAnimalsForm,
    MedicalRecordForm,
    UploadAppendixForm,
)
from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord, MedicalRecordAttachment
from ahc.apps.medical_notes.selectors import (
    animal_choices_for,
    available_months_for,
    can_access_note_animal,
    is_attachment_author,
    page_of_month,
    timeline_for,
)
from ahc.apps.medical_notes.services.attachments import (
    AttachmentLimitExceeded,
    delete_attachment,
    download_attachment,
    upload_attachment,
)
from ahc.apps.medical_notes.services.notes import create_note, next_route_for, update_note
from ahc.apps.medical_notes.views.mixins.user_animal_permisions import (
    AnimalDirectAccessRequiredMixin,
    AttachmentAuthorRequiredMixin,
    NoteAuthorRequiredMixin,
)


class CreateNoteFormView(LoginRequiredMixin, AnimalDirectAccessRequiredMixin, FormView):
    template_name = "medical_notes/create.html"
    form_class = MedicalRecordForm

    def get_template_names(self):
        if self.request.headers.get("HX-Request"):
            return ["partials/modal_note_form.html"]
        return [self.template_name]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["animal_choices"] = animal_choices_for(self.request.user.profile, exclude_id=self.kwargs.get("pk"))
        kwargs["type_of_event_param"] = self.request.GET.get("type_of_event")
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_name"] = str(self.form_class.__name__)
        context["form_action"] = self.request.get_full_path()
        legend_map = {
            "medical_visit": "Add vet visit",
            "diet_note": "Diet note",
            "biometric_record": "Biometric record",
            "medicament_note": "Medicament note",
            "fast_note": "Quick note",
        }
        context["legend"] = legend_map.get(self.request.GET.get("type_of_event", ""), "New note")
        return context

    def form_valid(self, form):
        animal_id = self.kwargs.get("pk")
        animal = get_object_or_404(AnimalProfile, id=animal_id)
        note = create_note(self.request.user.profile, animal, form)
        uploaded_file = self.request.FILES.get("attachment_file")
        if uploaded_file:
            try:
                upload_attachment(
                    medical_record=note,
                    attachment_instance=MedicalRecordAttachment(),
                    uploaded_file=uploaded_file,
                )
            except AttachmentLimitExceeded as exc:
                messages.warning(self.request, f"Note saved but attachment upload failed: {exc}")
        url_name, kwargs = next_route_for(note, animal_id)
        redirect_url = reverse(url_name, kwargs=kwargs)
        if self.request.headers.get("HX-Request"):
            response = HttpResponse(status=204)
            response["HX-Redirect"] = redirect_url
            return response
        return redirect(redirect_url)

    def get_success_url(self):
        animal_id = self.kwargs.get("pk")
        return reverse("animal_profile", kwargs={"pk": animal_id})


class FullTimelineOfNotes(LoginRequiredMixin, AnimalDirectAccessRequiredMixin, ListView):
    model = MedicalRecord
    template_name = "medical_notes/full_timeline_of_notes.html"
    context_object_name = "notes"
    paginate_by = 4

    def get_template_names(self):
        if self.request.headers.get("HX-Request"):
            return ["medical_notes/partials/_timeline_page.html"]
        return [self.template_name]

    def get_queryset(self):
        self._animal = get_object_or_404(AnimalProfile, id=self.kwargs.get("pk"))
        return timeline_for(
            self._animal,
            type_of_event=self.request.GET.get("type_of_event"),
            tag_name=self.request.GET.get("tag_name"),
        ).order_by("-date_creation")

    def paginate_queryset(self, queryset, page_size):
        month_param = self.request.GET.get("month")
        if month_param and not self.request.GET.get("page"):
            try:
                target_date = datetime.strptime(month_param, "%Y-%m").date()
                page_num = page_of_month(queryset, target_date, page_size)
                self.kwargs[self.page_kwarg] = page_num
            except ValueError:
                pass
        return super().paginate_queryset(queryset, page_size)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        page_notes = list(context["page_obj"])
        upload_forms = []
        for note in page_notes:
            form = UploadAppendixForm()
            form.fields["medical_record_id"].initial = str(note.id)
            upload_forms.append(form)
        context["notes"] = zip(page_notes, upload_forms, strict=False)

        type_of_event = self.request.GET.get("type_of_event", "")
        tag_name = self.request.GET.get("tag_name", "")
        context["available_months"] = available_months_for(
            self._animal,
            type_of_event=type_of_event or None,
            tag_name=tag_name or None,
        )
        context["scroll_to_month"] = self.request.GET.get("month", "")
        context["type_of_event"] = type_of_event
        context["tag_name"] = tag_name
        base_parts = []
        if type_of_event:
            base_parts.append(f"type_of_event={type_of_event}")
        if tag_name:
            base_parts.append(f"tag_name={tag_name}")
        context["base_query"] = "&".join(base_parts)

        return context

    def post(self, request, *args, **kwargs):
        form = UploadAppendixForm(request.POST, request.FILES)
        if form.is_valid():
            medical_record_id = form["medical_record_id"].value()
            medical_record = get_object_or_404(MedicalRecord, id=medical_record_id)
            form.save(commit=False)
            try:
                upload_attachment(
                    medical_record=medical_record,
                    attachment_instance=form.instance,
                    uploaded_file=request.FILES["file"],
                )
                messages.success(request, "Attachment uploaded successfully.")
            except AttachmentLimitExceeded as exc:
                messages.error(request, f"Failed to upload. {exc}")
        else:
            for _field, errors in form.errors.items():
                messages.error(request, f"Failed to upload: {', '.join(str(e) for e in errors)}")

        return redirect(request.get_full_path())


class EditNoteView(LoginRequiredMixin, NoteAuthorRequiredMixin, UpdateView):
    model = MedicalRecord
    form_class = MedicalRecordEditForm
    template_name = "medical_notes/edit.html"
    context_object_name = "note"

    def get_template_names(self):
        if self.request.headers.get("HX-Request"):
            return ["partials/modal_note_form.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_action"] = self.request.get_full_path()
        context["legend"] = f"Edit note for {self.object.animal.full_name}"
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["animal_choices"] = animal_choices_for(self.request.user.profile)

        note = get_object_or_404(MedicalRecord, pk=self.kwargs.get("pk"))
        kwargs["animal"] = get_object_or_404(AnimalProfile, id=note.animal.id)

        return kwargs

    def form_valid(self, form):
        note = get_object_or_404(MedicalRecord, id=self.kwargs.get("pk"))
        update_note(note, form)
        uploaded_file = self.request.FILES.get("attachment_file")
        if uploaded_file:
            try:
                upload_attachment(
                    medical_record=note,
                    attachment_instance=MedicalRecordAttachment(),
                    uploaded_file=uploaded_file,
                )
            except AttachmentLimitExceeded as exc:
                messages.warning(self.request, f"Note saved but attachment upload failed: {exc}")
        if self.request.headers.get("HX-Request"):
            response = HttpResponse(status=204)
            response["HX-Redirect"] = self.get_success_url()
            return response
        return super().form_valid(form)

    def get_success_url(self):
        note = get_object_or_404(MedicalRecord, pk=self.kwargs.get("pk"))
        return reverse("full_timeline_of_notes", kwargs={"pk": note.animal.id})


class EditMedicalRecordAttachmentDescription(LoginRequiredMixin, AttachmentAuthorRequiredMixin, UpdateView):
    model = MedicalRecordAttachment
    fields = ["description"]
    template_name = "medical_notes/edit.html"

    def get_success_url(self):
        attachment = get_object_or_404(MedicalRecordAttachment, pk=self.kwargs.get("pk"))
        return reverse("full_timeline_of_notes", kwargs={"pk": attachment.medical_record.animal.id})


class EditRelatedAnimalsView(EditNoteView):
    model = MedicalRecord
    form_class = MedicalRecordEditRelatedAnimalsForm
    template_name = "medical_notes/edit.html"
    context_object_name = "note"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        user = self.request.user.profile
        kwargs["is_author"] = MedicalRecord.objects.filter(author=user).exists()
        return kwargs

    def test_func(self):
        note = get_object_or_404(MedicalRecord, pk=self.kwargs.get("pk"))
        return can_access_note_animal(self.request.user.profile, note)


class DeleteMedicalRecordAttachment(LoginRequiredMixin, AttachmentAuthorRequiredMixin, DeleteView):
    model = MedicalRecordAttachment
    template_name = "medical_notes/delete_confirm.html"
    context_object_name = "note"

    def get_success_url(self):
        attachment = get_object_or_404(MedicalRecordAttachment, pk=self.kwargs.get("pk"))
        return reverse("full_timeline_of_notes", kwargs={"pk": attachment.medical_record.animal.id})

    def form_valid(self, form):
        self.object = self.get_object()
        success_url = self.get_success_url()
        delete_attachment(self.object)
        return redirect(success_url)


class DeleteNoteView(LoginRequiredMixin, NoteAuthorRequiredMixin, DeleteView):
    model = MedicalRecord
    template_name = "medical_notes/delete_confirm.html"
    context_object_name = "note"

    def get_success_url(self):
        note = get_object_or_404(MedicalRecord, pk=self.kwargs.get("pk"))
        return reverse("full_timeline_of_notes", kwargs={"pk": note.animal.id})


class DownloadAttachmentView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Download attachment by CouchDB reference id (URL kwarg: id, not pk)."""

    def test_func(self):
        attachment = get_object_or_404(MedicalRecordAttachment, couch_id=self.kwargs.get("id"))
        return is_attachment_author(self.request.user.profile, attachment)

    def get(self, request, *args, **kwargs):
        reference_id = self.kwargs.get("id")
        file_data, file_name = download_attachment(reference_id)
        response = HttpResponse(file_data, content_type="application/octet-stream")
        response["Content-Disposition"] = f'attachment; filename="{file_name}"'
        return response
