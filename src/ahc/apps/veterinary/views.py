from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Model
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import CreateView, DeleteView, TemplateView, UpdateView

from ahc.apps.veterinary.forms import MedicalPlaceForm, VetForm
from ahc.apps.veterinary.models import MedicalPlace, Vet
from ahc.apps.veterinary.selectors import animals_referencing, medical_places_for, vets_for
from ahc.apps.veterinary.services import create_contact, delete_contact

if TYPE_CHECKING:
    from ahc.types import AuthenticatedRequest


def _safe_next(request) -> str | None:
    candidate = request.POST.get("next") or request.GET.get("next")
    if candidate and url_has_allowed_host_and_scheme(
        candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return candidate
    return None


class ContactBookView(LoginRequiredMixin, TemplateView):
    template_name = "veterinary/contact_book.html"
    request: AuthenticatedRequest

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.profile
        context["vets"] = vets_for(profile)
        context["medical_places"] = medical_places_for(profile)
        return context


class OwnedContactMixin:
    """Restrict lookup to the logged-in user's own records — anything else 404s, never 403."""

    request: AuthenticatedRequest
    model: type[Model]

    def get_queryset(self):
        return self.model.objects.filter(owner=self.request.user.profile)


class ContactCreateView(LoginRequiredMixin, CreateView):
    kind_label: str
    template_name = "veterinary/contact_form.html"
    request: AuthenticatedRequest

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.request.user.profile
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["kind_label"] = self.kind_label
        context["next"] = _safe_next(self.request) or ""
        return context

    def form_valid(self, form):
        self.object = create_contact(self.request.user.profile, form)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return _safe_next(self.request) or reverse("contact_book")


class ContactUpdateView(LoginRequiredMixin, OwnedContactMixin, UpdateView):
    kind_label: str
    template_name = "veterinary/contact_form.html"
    request: AuthenticatedRequest

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["owner"] = self.request.user.profile
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["kind_label"] = self.kind_label
        context["next"] = _safe_next(self.request) or ""
        return context

    def get_success_url(self):
        return _safe_next(self.request) or reverse("contact_book")


class ContactDeleteView(LoginRequiredMixin, OwnedContactMixin, DeleteView):
    kind_label: str
    template_name = "veterinary/contact_confirm_delete.html"
    request: AuthenticatedRequest

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["kind_label"] = self.kind_label
        context["referencing_animals"] = animals_referencing(self.object)
        return context

    def form_valid(self, form):
        delete_contact(self.object)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("contact_book")


class VetCreateView(ContactCreateView):
    model = Vet
    form_class = VetForm
    kind_label = "vet"


class VetUpdateView(ContactUpdateView):
    model = Vet
    form_class = VetForm
    kind_label = "vet"


class VetDeleteView(ContactDeleteView):
    model = Vet
    kind_label = "vet"


class MedicalPlaceCreateView(ContactCreateView):
    model = MedicalPlace
    form_class = MedicalPlaceForm
    kind_label = "medical place"


class MedicalPlaceUpdateView(ContactUpdateView):
    model = MedicalPlace
    form_class = MedicalPlaceForm
    kind_label = "medical place"


class MedicalPlaceDeleteView(ContactDeleteView):
    model = MedicalPlace
    kind_label = "medical place"
