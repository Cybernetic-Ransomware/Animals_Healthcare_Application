from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.generic import TemplateView, View
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView

from ahc.apps.animals.forms import AnimalRegisterForm, PinAnimalForm
from ahc.apps.animals.models import Animal
from ahc.apps.animals.selectors import (
    allowed_categories_for,
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
    categories: frozenset[str] = frozenset()


def _build_mainpage(request, animal: Animal, allowed: set[str] | None = None) -> dict[str, Any]:
    return {}


_TIMELINE_PER_PAGE = 20


def _timeline_boundary_from_month(month_param: str) -> datetime | None:
    """Return the start of the month AFTER month_param as an aware local datetime.

    Used to filter records for a month-jump: records with date_creation < boundary
    start exactly at the end of the target month.  Returns None on parse failure.
    """
    try:
        target = date.fromisoformat(month_param + "-01")
    except ValueError:
        return None
    first_of_next = date(target.year + 1, 1, 1) if target.month == 12 else date(target.year, target.month + 1, 1)
    tz = timezone.get_current_timezone()
    return timezone.make_aware(datetime(first_of_next.year, first_of_next.month, first_of_next.day, 0, 0, 0), tz)


def _build_vet(request, animal: Animal, allowed: set[str] | None = None) -> dict[str, Any]:
    ctx: dict[str, Any] = {}
    if allowed is None or "vet_contact" in allowed:
        ctx["show_vet_contact"] = True

    if allowed is None or "history" in allowed:
        from ahc.apps.medical_notes.selectors import available_months_for, timeline_for

        qs = timeline_for(animal, type_of_event="medical_visit").order_by("-date_creation")

        month_param = request.GET.get("month")
        before_param = request.GET.get("before")

        if month_param and not before_param:
            boundary = _timeline_boundary_from_month(month_param)
            if boundary:
                qs = qs.filter(date_creation__lt=boundary)
        elif before_param:
            before_dt = parse_datetime(before_param)
            if before_dt:
                qs = qs.filter(date_creation__lt=before_dt)

        records = list(qs[: _TIMELINE_PER_PAGE + 1])
        tl_has_more = len(records) > _TIMELINE_PER_PAGE
        if tl_has_more:
            records = records[:_TIMELINE_PER_PAGE]

        ctx.update(
            {
                "vet_records": records,
                "tl_has_more": tl_has_more,
                "tl_next_before": records[-1].date_creation.isoformat() if records else None,
                "tl_slug": "vet",
                "scroll_to_month": month_param or "",
                "available_months": available_months_for(animal, type_of_event="medical_visit"),
            }
        )
    return ctx


def _build_diet(request, animal: Animal, allowed: set[str] | None = None) -> dict[str, Any]:
    if allowed is not None and "diet" not in allowed:
        return {}
    from ahc.apps.medical_notes.selectors import timeline_for

    return {
        "diet_records": timeline_for(animal, type_of_event="diet_note").order_by("-date_creation"),
    }


def _build_medications(request, animal: Animal, allowed: set[str] | None = None) -> dict[str, Any]:
    if allowed is not None and "medications" not in allowed:
        return {}
    from ahc.apps.medical_notes.selectors import medication_notes_for

    return {"medication_records": medication_notes_for(animal)}


def _build_notes(request, animal: Animal, allowed: set[str] | None = None) -> dict[str, Any]:
    ctx: dict[str, Any] = {}

    if allowed is None or "history" in allowed:
        from ahc.apps.medical_notes.selectors import other_history_for

        qs = other_history_for(animal)

        month_param = request.GET.get("month")
        before_param = request.GET.get("before")

        if month_param and not before_param:
            boundary = _timeline_boundary_from_month(month_param)
            if boundary:
                qs = qs.filter(date_creation__lt=boundary)
        elif before_param:
            before_dt = parse_datetime(before_param)
            if before_dt:
                qs = qs.filter(date_creation__lt=before_dt)

        records = list(qs[: _TIMELINE_PER_PAGE + 1])
        tl_has_more = len(records) > _TIMELINE_PER_PAGE
        if tl_has_more:
            records = records[:_TIMELINE_PER_PAGE]

        available_months = list(
            other_history_for(animal).datetimes(
                "date_creation",
                "month",
                order="DESC",
                tzinfo=timezone.get_current_timezone(),
            )
        )

        ctx.update(
            {
                "other_records": records,
                "tl_has_more": tl_has_more,
                "tl_next_before": records[-1].date_creation.isoformat() if records else None,
                "tl_slug": "notes",
                "scroll_to_month": month_param or "",
                "available_months": available_months,
            }
        )

    if allowed is None or "biometrics" in allowed:
        from ahc.apps.medical_notes.selectors import biometric_records_for

        ctx["biometric_records"] = biometric_records_for(animal)

    return ctx


def _build_ownership(request, animal: Animal, allowed: set[str] | None = None) -> dict[str, Any]:
    return {"keepers": animal.shares.select_related("carer__user").all()}


def _build_settings(request, animal: Animal, allowed: set[str] | None = None) -> dict[str, Any]:
    return {}


def _build_vaccinations(request, animal: Animal, allowed: set[str] | None = None) -> dict[str, Any]:
    if allowed is not None and "vaccinations" not in allowed:
        return {}
    from ahc.apps.medical_notes.selectors import vaccination_notes_for

    return {"vaccination_records": vaccination_notes_for(animal)}


TAB_REGISTRY: dict[str, Tab] = {
    tab.slug: tab
    for tab in [
        Tab(
            "mainpage",
            "Overview",
            "animals/tabs/_mainpage.html",
            False,
            _build_mainpage,
            frozenset({"basic"}),
        ),
        Tab(
            "vet",
            "Vet & Visits",
            "animals/tabs/_vet.html",
            False,
            _build_vet,
            frozenset({"vet_contact", "history"}),
        ),
        Tab(
            "diet",
            "Diet",
            "animals/tabs/_diet.html",
            False,
            _build_diet,
            frozenset({"diet"}),
        ),
        Tab(
            "medications",
            "Medications",
            "animals/tabs/_medications.html",
            False,
            _build_medications,
            frozenset({"medications"}),
        ),
        Tab(
            "notes",
            "Notes",
            "animals/tabs/_notes.html",
            False,
            _build_notes,
            frozenset({"history", "biometrics"}),
        ),
        Tab(
            "vaccinations",
            "Vaccinations",
            "animals/tabs/_vaccinations.html",
            False,
            _build_vaccinations,
            frozenset({"vaccinations"}),
        ),
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
    allowed = allowed_categories_for(profile, animal)

    def _tab_visible(tab: Tab) -> bool:
        if tab.owner_only:
            return owner
        if not tab.categories:
            return True
        return owner or bool(tab.categories & allowed)

    return {
        "now": timezone.now().date(),
        "is_owner": owner,
        "is_pinned": is_pinned(profile, animal),
        "allowed_categories": allowed,
        "tabs": [t for t in TABS_LIST if _tab_visible(t)],
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
        base = _base_profile_context(self.request, self.object)
        context.update(base)
        context["active_tab"] = DEFAULT_TAB_SLUG
        context["active_partial"] = TAB_REGISTRY[DEFAULT_TAB_SLUG].template
        context.update(TAB_REGISTRY[DEFAULT_TAB_SLUG].build(self.request, self.object, allowed=base["allowed_categories"]))
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
        profile = self.request.user.profile
        if not user_can_access_animal(profile, animal):
            return False
        tab = TAB_REGISTRY.get(self.kwargs.get("slug", ""))
        if tab is None:
            return True
        if tab.owner_only:
            return is_animal_owner(profile, animal)
        if tab.categories and not is_animal_owner(profile, animal):
            allowed = allowed_categories_for(profile, animal)
            return bool(tab.categories & allowed)
        return True

    def get_template_names(self):
        tab = self._get_tab()
        if self.request.headers.get("HX-Request"):
            if self.request.GET.get("load_more") and tab.slug in ("vet", "notes"):
                return [f"animals/tabs/partials/_timeline_nodes_{tab.slug}.html"]
            return [tab.template]
        return ["animals/profile.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tab = self._get_tab()
        base = _base_profile_context(self.request, self.object)
        context.update(base)
        context["active_tab"] = tab.slug
        context["active_partial"] = tab.template
        context.update(tab.build(self.request, self.object, allowed=base["allowed_categories"]))
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
