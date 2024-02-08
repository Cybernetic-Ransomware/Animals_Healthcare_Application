from animals.models import Animal as AnimalProfile
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic.edit import DeleteView, FormView, UpdateView
from django.views.generic.list import ListView
from medical_notes.forms.type_basic_note import (
    MedicalRecordEditForm,
    MedicalRecordEditRelatedAnimalsForm,
    MedicalRecordForm,
    UploadAppendixForm,
)
from medical_notes.models.type_basic_note import MedicalRecord, MedicalRecordAttachment

# UploadAppendixFormSet = formset_factory(UploadAppendixForm, extra=0)


# append viewing other related animals on note_views and notelist
class CreateNoteFormView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = "medical_notes/create.html"
    form_class = MedicalRecordForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        query = (
            AnimalProfile.objects.filter(
                Q(owner=self.request.user.profile) | Q(allowed_users=self.request.user.profile)
            )
            .exclude(id=self.kwargs.get("pk"))
            .order_by("-creation_date")
        )

        animal_choices = [(animal.id, animal.full_name) for animal in query]
        kwargs["animal_choices"] = animal_choices
        kwargs["type_of_event_param"] = self.request.GET.get("type_of_event")
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_name"] = str(self.form_class.__name__)
        return context

    def form_valid(self, form):
        animal_id = self.kwargs.get("pk")
        animal = get_object_or_404(AnimalProfile, id=animal_id)

        new_note = form.save(commit=False)
        new_note.animal = animal
        new_note.author = self.request.user.profile
        new_note.save()
        form.save_m2m()

        # return super().form_valid(form)
        type_of_event = form.cleaned_data.get("type_of_event")

        if type_of_event == "biometric_record":
            medical_create_url = reverse("biometric_create", kwargs={"pk": animal_id, "note_id": new_note.id})
            return redirect(medical_create_url)
        elif type_of_event == "diet_note":
            medical_create_url = reverse("feeding_create", kwargs={"pk": new_note.id})
            return redirect(medical_create_url)
        else:
            full_timeline_url = reverse("full_timeline_of_notes", kwargs={"pk": animal_id})
            return redirect(full_timeline_url)

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
        query = MedicalRecord.objects.filter(animal=animal)

        type_of_event = self.request.GET.get("type_of_event")
        if type_of_event:
            query = query.filter(type_of_event=type_of_event)

        tag_name = self.request.GET.get("tag_name")
        if tag_name:
            query = query.filter(note_tags__slug=tag_name)

        query = query.prefetch_related("attachments")

        paginator = Paginator(list(query.order_by("-date_creation")), per_page=self.paginate_by)
        page_number = self.request.GET.get("page")

        notes = paginator.get_page(page_number)

        upload_forms = []
        for note in context["notes"]:
            form = UploadAppendixForm()
            form.fields["medical_record_id"].initial = str(note.id)
            upload_forms.append(form)

        notes_with_forms = zip(context["notes"], upload_forms)

        context["notes"] = notes_with_forms

        return context

    def post(self, request, *args, **kwargs):
        form = UploadAppendixForm(request.POST, request.FILES)
        if form.is_valid():
            medical_record_id = form["medical_record_id"].value()
            medical_record = get_object_or_404(MedicalRecord, id=medical_record_id)

            attachments_count = MedicalRecordAttachment.objects.filter(medical_record=medical_record_id).count()
            attanents_limit_per_note = settings.COUCH_DB_LIMIT_PER_NOTE
            if attachments_count >= attanents_limit_per_note:
                messages.error(
                    request,
                    f"Failed to upload. Maximum limit {attanents_limit_per_note} attachments per note is already reached.",
                )
                return redirect(request.path)

            with transaction.atomic():
                form.instance.medical_record = medical_record
                form.save()

                couch_connector = settings.COUCH_DB

                uploaded_file = request.FILES["file"]
                file_reference_uuid = str(form.instance.id)
                uploaded_file_name = uploaded_file.name
                uploaded_file.seek(0)
                blop_file = uploaded_file.read()

                couch_connector.save({"_id": file_reference_uuid, "name": uploaded_file_name})

                doc_dict = couch_connector.get(file_reference_uuid)
                couch_connector.put_attachment(doc_dict, blop_file, filename=uploaded_file_name)

                messages.success(request, "Attachment uploaded successfully.")

        else:
            print(form.errors)
            for field, errors in form.errors.items():
                messages.error(request, f"Failed to upload: {', '.join(errors)}")

        return redirect(request.path)

    def render_to_response(self, context, **response_kwargs):
        return super().render_to_response(context, **response_kwargs)

    def test_func(self):
        user = self.request.user.profile

        animal_id = self.kwargs.get("pk")
        animal = get_object_or_404(AnimalProfile, id=animal_id)

        all_users = set(animal.allowed_users.all())
        all_users.add(animal.owner)

        return user in all_users


class EditNoteView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = MedicalRecord
    form_class = MedicalRecordEditForm
    template_name = "medical_notes/edit.html"
    context_object_name = "note"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        query = AnimalProfile.objects.filter(
            Q(owner=self.request.user.profile) | Q(allowed_users=self.request.user.profile)
        ).order_by("-creation_date")

        animal_choices = [(animal.id, animal.full_name) for animal in query]
        kwargs["animal_choices"] = animal_choices

        note_id = self.kwargs.get("pk")
        note = get_object_or_404(MedicalRecord, pk=note_id)
        animal_id = note.animal.id
        animal = get_object_or_404(AnimalProfile, id=animal_id)
        kwargs["animal"] = animal

        return kwargs

    def form_valid(self, form):
        note_id = self.kwargs.get("pk")
        note = get_object_or_404(MedicalRecord, id=note_id)

        if "animal" in form.cleaned_data:
            note.animal = form.cleaned_data["animal"]

        note.save()

        additional_animals = form.cleaned_data.get("additional_animals")
        note.additional_animals.set(additional_animals)

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


class EditMedicalRecordAttachmentDescription(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = MedicalRecordAttachment
    fields = ["description"]
    template_name = "medical_notes/edit.html"

    def get_success_url(self):
        attachment_id = self.kwargs.get("pk")
        attachment = get_object_or_404(MedicalRecordAttachment, pk=attachment_id)
        note = attachment.medical_record
        animal_id = note.animal.id
        return reverse("full_timeline_of_notes", kwargs={"pk": animal_id})

    def test_func(self):
        user = self.request.user.profile

        attachment_id = self.kwargs.get("pk")
        attachment = get_object_or_404(MedicalRecordAttachment, pk=attachment_id)
        note_author = attachment.medical_record.author
        return user == note_author


class EditRelatedAnimalsView(EditNoteView):
    model = MedicalRecord
    form_class = MedicalRecordEditRelatedAnimalsForm
    template_name = "medical_notes/edit.html"
    context_object_name = "note"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        user = self.request.user.profile
        author = MedicalRecord.objects.filter(author=user)

        kwargs["is_author"] = author.exists()

        return kwargs

    def test_func(self):
        user = self.request.user.profile

        note_id = self.kwargs.get("pk")
        note = get_object_or_404(MedicalRecord, pk=note_id)
        animal_id = note.animal.id
        animal = get_object_or_404(AnimalProfile, id=animal_id)

        all_users = set(animal.allowed_users.all())
        all_users.add(animal.owner)

        return user in all_users


class DeleteNoteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = MedicalRecord
    template_name = "medical_notes/delete_confirm.html"
    context_object_name = "note"

    def test_func(self):
        user = self.request.user.profile

        note_id = self.kwargs.get("pk")
        note_author = get_object_or_404(MedicalRecord, id=note_id).author

        return user == note_author

    def get_success_url(self):
        note_id = self.kwargs.get("pk")
        note = get_object_or_404(MedicalRecord, pk=note_id)
        animal_id = note.animal.id
        return reverse("full_timeline_of_notes", kwargs={"pk": animal_id})
