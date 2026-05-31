from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView, View
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView

from ahc.apps.animals.forms import AnimalRegisterForm, PinAnimalForm
from ahc.apps.animals.models import Animal
from ahc.apps.animals.selectors import (
    animals_visible_to,
    is_animal_owner,
    is_pinned,
    user_can_access_animal,
)
from ahc.apps.animals.services import create_animal, pin_animal, unpin_animal


@dataclass
class Tab:
    slug: str
    label: str
    template: str
    owner_only: bool
    build: Callable[..., dict[str, Any]]


def _build_mainpage(request, animal: Animal) -> dict[str, Any]:
    return {}


def _build_vet(request, animal: Animal) -> dict[str, Any]:
    from ahc.apps.medical_notes.selectors import timeline_for

    return {
        "vet_records": timeline_for(animal, type_of_event="medical_visit").order_by("-date_creation"),
    }


def _build_diet(request, animal: Animal) -> dict[str, Any]:
    from ahc.apps.medical_notes.selectors import timeline_for

    return {
        "diet_records": timeline_for(animal, type_of_event="diet_note").order_by("-date_creation"),
    }


def _build_medications(request, animal: Animal) -> dict[str, Any]:
    from ahc.apps.medical_notes.selectors import medication_notes_for

    return {"medication_records": medication_notes_for(animal)}


def _build_notes(request, animal: Animal) -> dict[str, Any]:
    from ahc.apps.medical_notes.selectors import other_records_for

    return {"other_records": other_records_for(animal)}


def _build_ownership(request, animal: Animal) -> dict[str, Any]:
    return {"keepers": animal.allowed_users.all()}


def _build_settings(request, animal: Animal) -> dict[str, Any]:
    return {}


TAB_REGISTRY: dict[str, Tab] = {
    tab.slug: tab
    for tab in [
        Tab("mainpage", "Overview", "animals/tabs/_mainpage.html", False, _build_mainpage),
        Tab("vet", "Vet & Visits", "animals/tabs/_vet.html", False, _build_vet),
        Tab("diet", "Diet", "animals/tabs/_diet.html", False, _build_diet),
        Tab("medications", "Medications", "animals/tabs/_medications.html", False, _build_medications),
        Tab("notes", "Notes", "animals/tabs/_notes.html", False, _build_notes),
        Tab("ownership", "Ownership", "animals/tabs/_ownership.html", True, _build_ownership),
        Tab("settings", "Settings", "animals/tabs/_settings.html", True, _build_settings),
    ]
}

TABS_LIST: list[Tab] = list(TAB_REGISTRY.values())

DEFAULT_TAB_SLUG = "mainpage"


def _base_profile_context(request, animal: Animal) -> dict[str, Any]:
    """Shared context for profile.html shell and AnimalTabView."""
    profile = request.user.profile
    owner = is_animal_owner(profile, animal)
    return {
        "now": timezone.now().date(),
        "is_owner": owner,
        "is_pinned": is_pinned(profile, animal),
        # Non-owners do not see owner-only tabs in the nav bar.
        "tabs": [t for t in TABS_LIST if not t.owner_only or owner],
    }


class CreateAnimalView(LoginRequiredMixin, FormView):
    template_name = "animals/create.html"
    form_class = AnimalRegisterForm
    success_url = "/animals/"

    def form_valid(self, form):
        new_animal = create_animal(self.request.user.profile, form)
        self.success_url = reverse("animal_profile", kwargs={"pk": new_animal.id})
        return super().form_valid(form)


class AnimalProfileDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Entry point for the animal profile page.

    Renders the full shell (profile.html) with the default tab active.
    Tab content is served by AnimalTabView when htmx requests a fragment.
    """

    model = Animal
    template_name = "animals/profile.html"
    context_object_name = "animal"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_base_profile_context(self.request, self.object))
        context["active_tab"] = DEFAULT_TAB_SLUG
        context["active_partial"] = TAB_REGISTRY[DEFAULT_TAB_SLUG].template
        context.update(TAB_REGISTRY[DEFAULT_TAB_SLUG].build(self.request, self.object))
        return context

    def test_func(self):
        animal = self.get_object()
        return user_can_access_animal(self.request.user.profile, animal)


class AnimalTabView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Serves individual tab content for the animal profile page.

    When called with HX-Request header (htmx): returns only the tab fragment.
    Without the header (direct navigation / JS disabled): returns the full shell
    so progressive enhancement works — every tab has a real fallback URL.
    """

    model = Animal
    context_object_name = "animal"

    def _get_tab(self) -> Tab:
        slug = self.kwargs.get("slug", "")
        tab = TAB_REGISTRY.get(slug)
        if tab is None:
            raise Http404(f"Unknown tab slug: {slug!r}")
        return tab

    def test_func(self):
        animal = self.get_object()
        if not user_can_access_animal(self.request.user.profile, animal):
            return False
        tab = TAB_REGISTRY.get(self.kwargs.get("slug", ""))
        if tab and tab.owner_only:
            return is_animal_owner(self.request.user.profile, animal)
        return True

    def get_template_names(self):
        tab = self._get_tab()
        if self.request.headers.get("HX-Request"):
            return [tab.template]
        return ["animals/profile.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tab = self._get_tab()
        context.update(_base_profile_context(self.request, self.object))
        context["active_tab"] = tab.slug
        context["active_partial"] = tab.template
        context.update(tab.build(self.request, self.object))
        return context


class StableView(LoginRequiredMixin, TemplateView):
    template_name = "animals/all_animals_stable.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["animals"] = animals_visible_to(self.request.user.profile)
        return context


class ToPinAnimalsView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = PinAnimalForm(request.POST)
        profile = request.user.profile

        if form.is_valid():
            animal_id = form.cleaned_data["animal_id"]
            action = form.cleaned_data["action"]

            if action == "add":
                try:
                    pin_animal(profile, animal_id)
                except PermissionError:
                    return JsonResponse({"status": "forbidden"}, status=403)
            elif action == "remove":
                unpin_animal(profile, animal_id)

        return JsonResponse({"status": "success"})
