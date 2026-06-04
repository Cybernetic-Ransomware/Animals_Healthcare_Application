from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import DeleteView, View
from django.views.generic.edit import FormView

from ahc.apps.animals.mixins.animal_owner_permissions import UserPassesOwnershipTestMixin
from ahc.apps.animals.models import Animal, AnimalShare
from ahc.apps.animals.services import (
    create_share,
    process_profile_image,
    remove_keeper,
    set_animal_details,
    set_birthday,
    set_dietary_restrictions,
    set_first_contact,
    set_next_visit,
    transfer_ownership,
    update_share,
)
from ahc.apps.animals.utils_owner.forms import (
    ChangeAnimalDetailsForm,
    ChangeBirthdayForm,
    ChangeDietaryRestrictionsForm,
    ChangeFirstContactForm,
    ChangeNextVisitForm,
    ChangeOwnerForm,
    EditShareForm,
    ImageUploadForm,
    ManageKeepersForm,
)

if TYPE_CHECKING:
    from ahc.types import AuthenticatedRequest


class AnimalDeleteView(LoginRequiredMixin, UserPassesOwnershipTestMixin, DeleteView):
    model = Animal
    template_name = "animals/animal_confirm_delete.html"
    success_url = reverse_lazy("Homepage")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["animal_id"] = self.kwargs["pk"]
        return context


class ImageUploadView(LoginRequiredMixin, UserPassesOwnershipTestMixin, FormView):
    template_name = "animals/image.html"
    form_class = ImageUploadForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["animal_id"] = self.kwargs["pk"]
        return context  # to the template

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        animal_id = self.kwargs["pk"]
        kwargs["instance"] = Animal.objects.get(id=animal_id)
        return kwargs

    def form_valid(self, form):
        form.save()
        process_profile_image(form.instance)
        success_url = reverse("animal_profile", kwargs={"pk": form.instance.pk})
        return redirect(success_url)


class ChangeOwnerView(LoginRequiredMixin, UserPassesOwnershipTestMixin, FormView):
    template_name = "animals/change_owner.html"
    form_class = ChangeOwnerForm
    request: AuthenticatedRequest

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        animal = Animal.objects.get(pk=self.kwargs["pk"])
        context["full_name"] = animal.full_name
        context["animal_url"] = reverse("animal_profile", kwargs={"pk": self.get_form().instance.id})
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = Animal.objects.get(pk=self.kwargs["pk"])
        return kwargs

    def form_valid(self, form):
        transfer_ownership(
            animal=form.instance,
            new_owner=form.cleaned_data["new_owner"],
            set_keeper=form.cleaned_data["set_keeper"],
            requesting_profile=self.request.user.profile,
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("animals_stable")


class ManageKeepersView(LoginRequiredMixin, UserPassesOwnershipTestMixin, FormView):
    template_name = "animals/manage_keepers.html"
    form_class = ManageKeepersForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        animal = Animal.objects.get(pk=self.kwargs["pk"])
        context["full_name"] = animal.full_name
        context["shares"] = animal.shares.select_related("carer__user").all()  # type: ignore
        context["animal_url"] = reverse("animal_profile", kwargs={"pk": self.get_form().instance.id})
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = Animal.objects.get(pk=self.kwargs["pk"])
        return kwargs

    def form_valid(self, form):
        cd = form.cleaned_data
        scope = {
            "allow_basic": cd["allow_basic"],
            "allow_vet_contact": cd["allow_vet_contact"],
            "allow_diet": cd["allow_diet"],
            "allow_medications": cd["allow_medications"],
            "allow_history": cd["allow_history"],
            "allow_biometrics": cd["allow_biometrics"],
        }
        create_share(form.instance, cd["input_user"], scope=scope, valid_until=cd.get("valid_until"))
        return super().form_valid(form)

    def get_success_url(self):
        return self.request.path


class ChangeBirthdayView(LoginRequiredMixin, UserPassesOwnershipTestMixin, FormView):
    form_class = ChangeBirthdayForm
    template_name = "animals/change_birthday.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = get_object_or_404(Animal, pk=self.kwargs["pk"])
        # print(kwargs["instance"])
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["animal_id"] = self.kwargs["pk"]
        return context

    def form_valid(self, form):
        set_birthday(get_object_or_404(Animal, pk=self.kwargs["pk"]), form.cleaned_data["birthdate"])
        success_url = reverse("animal_profile", kwargs={"pk": self.kwargs["pk"]})
        return redirect(success_url)


class ChangeFirstContactView(LoginRequiredMixin, UserPassesOwnershipTestMixin, FormView):
    form_class = ChangeFirstContactForm
    template_name = "animals/change_first_contact.html"

    def get_context_data(self, **kwargs):
        animal = get_object_or_404(Animal, pk=self.kwargs["pk"])
        context = super().get_context_data(**kwargs)
        context["animal_id"] = self.kwargs["pk"]
        context["vet"] = animal.first_contact_vet
        context["place"] = animal.first_contact_medical_place
        return context

    def form_valid(self, form):
        set_first_contact(
            get_object_or_404(Animal, pk=self.kwargs["pk"]),
            vet=form.cleaned_data["first_contact_vet"],
            place=form.cleaned_data["first_contact_medical_place"],
        )
        return super().form_valid(form)

    def get_success_url(self):
        return self.request.path


class ChangeNextVisitView(LoginRequiredMixin, UserPassesOwnershipTestMixin, FormView):
    form_class = ChangeNextVisitForm
    template_name = "animals/change_next_visit.html"

    def get_context_data(self, **kwargs):
        animal = get_object_or_404(Animal, pk=self.kwargs["pk"])
        context = super().get_context_data(**kwargs)
        context["animal_id"] = self.kwargs["pk"]
        context["next_visit_date"] = animal.next_visit_date
        return context

    def form_valid(self, form):
        set_next_visit(
            get_object_or_404(Animal, pk=self.kwargs["pk"]),
            next_visit_date=form.cleaned_data["next_visit_date"],
        )
        success_url = reverse("animal_tab", kwargs={"pk": self.kwargs["pk"], "slug": "vet"})
        return redirect(success_url)


class ChangeDietaryRestrictionsView(LoginRequiredMixin, UserPassesOwnershipTestMixin, FormView):
    form_class = ChangeDietaryRestrictionsForm
    template_name = "animals/change_dietary_restrictions.html"

    def get_context_data(self, **kwargs):
        animal = get_object_or_404(Animal, pk=self.kwargs["pk"])
        context = super().get_context_data(**kwargs)
        context["animal_id"] = self.kwargs["pk"]
        context["current_restrictions"] = animal.dietary_restrictions
        return context

    def form_valid(self, form):
        set_dietary_restrictions(
            get_object_or_404(Animal, pk=self.kwargs["pk"]),
            restrictions=form.cleaned_data["dietary_restrictions"],
        )
        success_url = reverse("animal_tab", kwargs={"pk": self.kwargs["pk"], "slug": "diet"})
        return redirect(success_url)


class ChangeAnimalDetailsView(LoginRequiredMixin, UserPassesOwnershipTestMixin, FormView):
    form_class = ChangeAnimalDetailsForm
    template_name = "animals/change_animal_details.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = get_object_or_404(Animal, pk=self.kwargs["pk"])
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["animal_id"] = self.kwargs["pk"]
        return context

    def form_valid(self, form):
        set_animal_details(
            get_object_or_404(Animal, pk=self.kwargs["pk"]),
            species=form.cleaned_data["species"],
            breed=form.cleaned_data["breed"],
            sex=form.cleaned_data["sex"],
            sterilization=form.cleaned_data["sterilization"],
        )
        success_url = reverse("animal_tab", kwargs={"pk": self.kwargs["pk"], "slug": "settings"})
        return redirect(success_url)


class RemoveKeeperView(LoginRequiredMixin, UserPassesOwnershipTestMixin, View):
    """Remove a single keeper from the animal's shares (owner-only, POST)."""

    def post(self, request, pk, keeper_pk):
        animal = get_object_or_404(Animal, pk=pk)
        remove_keeper(animal, keeper_pk)
        return redirect(reverse("animal_tab", kwargs={"pk": pk, "slug": "ownership"}))


class EditShareView(LoginRequiredMixin, UserPassesOwnershipTestMixin, FormView):
    """Edit the access scope and expiry date of an existing AnimalShare (owner-only)."""

    template_name = "animals/edit_share.html"
    form_class = EditShareForm

    def _get_share(self) -> AnimalShare:
        animal = get_object_or_404(Animal, pk=self.kwargs["pk"])
        return get_object_or_404(AnimalShare, animal=animal, carer_id=self.kwargs["keeper_pk"])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self._get_share()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["animal_id"] = self.kwargs["pk"]
        share = self._get_share()
        context["carer_name"] = share.carer.user.username
        return context

    def form_valid(self, form):
        cd = form.cleaned_data
        scope = {
            "allow_basic": cd["allow_basic"],
            "allow_vet_contact": cd["allow_vet_contact"],
            "allow_diet": cd["allow_diet"],
            "allow_medications": cd["allow_medications"],
            "allow_history": cd["allow_history"],
            "allow_biometrics": cd["allow_biometrics"],
        }
        update_share(form.instance, scope=scope, valid_until=cd.get("valid_until"))
        return redirect(reverse("animal_tab", kwargs={"pk": self.kwargs["pk"], "slug": "ownership"}))
