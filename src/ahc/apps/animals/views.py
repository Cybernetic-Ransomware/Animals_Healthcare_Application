from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
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
    deceased_animals_for,
    is_animal_owner,
    is_pinned,
    user_can_record_biometrics,
    user_can_view_animal,
)
from ahc.apps.animals.services import create_animal, pin_animal, unpin_animal

if TYPE_CHECKING:
    from ahc.types import AuthenticatedRequest


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


def _resolve_timeline_page(
    qs, month_param: str | None, before_param: str | None, before_pk_param: str | None
) -> tuple[list, bool]:
    """Filter/slice one page (qs ordered -date_creation, -pk); (date, pk) cursor avoids skipping ties at the boundary."""
    if month_param and not before_param:
        boundary = _timeline_boundary_from_month(month_param)
        if boundary:
            qs = qs.filter(date_creation__lt=boundary)
    elif before_param:
        before_dt = parse_datetime(before_param)
        if before_dt is None or not before_pk_param:
            return [], False
        try:
            before_pk = uuid.UUID(before_pk_param)
        except ValueError:
            return [], False
        qs = qs.filter(Q(date_creation__lt=before_dt) | Q(date_creation=before_dt, pk__lt=before_pk))

    records = list(qs[: _TIMELINE_PER_PAGE + 1])
    tl_has_more = len(records) > _TIMELINE_PER_PAGE
    if tl_has_more:
        records = records[:_TIMELINE_PER_PAGE]
    return records, tl_has_more


def _build_vet(request, animal: Animal, allowed: set[str] | None = None) -> dict[str, Any]:
    ctx: dict[str, Any] = {}
    if allowed is None or "vet_contact" in allowed:
        ctx["show_vet_contact"] = True

    if allowed is None or "history" in allowed:
        from ahc.apps.medical_notes.selectors import available_months_for, timeline_for

        qs = timeline_for(animal, type_of_event="medical_visit").order_by("-date_creation", "-pk")

        month_param = request.GET.get("month")
        before_param = request.GET.get("before")
        before_pk_param = request.GET.get("before_id")

        records, tl_has_more = _resolve_timeline_page(qs, month_param, before_param, before_pk_param)

        ctx.update(
            {
                "vet_records": records,
                "tl_has_more": tl_has_more,
                "tl_next_before": records[-1].date_creation.isoformat() if records else None,
                "tl_next_before_pk": records[-1].pk if records else None,
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

        qs = other_history_for(animal).order_by("-date_creation", "-pk")

        month_param = request.GET.get("month")
        before_param = request.GET.get("before")
        before_pk_param = request.GET.get("before_id")

        records, tl_has_more = _resolve_timeline_page(qs, month_param, before_param, before_pk_param)

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
                "tl_next_before_pk": records[-1].pk if records else None,
                "tl_slug": "notes",
                "scroll_to_month": month_param or "",
                "available_months": available_months,
            }
        )

    return ctx


def _resolve_biometric_date(record) -> date:
    """Return the best-known measurement date for a BiometricRecord.

    Cascade: the related note's user-entered date_event_started wins; otherwise fall
    back to the related note's date_creation; if the note itself was deleted
    (related_note is SET_NULL-able), fall back to BiometricRecord.date_updated, which
    despite its name is set once at creation (auto_now_add) and never changes.
    Both datetime fallbacks are localized before truncating to a date, since
    TIME_ZONE="Europe/Warsaw" means a naive `.date()` on stored UTC could land on the
    wrong day for entries made close to midnight.
    """
    note = record.related_note
    if note is not None:
        if note.date_event_started is not None:
            return note.date_event_started
        return timezone.localtime(note.date_creation).date()
    return timezone.localtime(record.date_updated).date()


def _build_biometrics(request, animal: Animal, allowed: set[str] | None = None) -> dict[str, Any]:
    if allowed is not None and "biometrics" not in allowed:
        return {}
    from ahc.apps.medical_notes.selectors import biometric_records_for_chart

    profile = request.user.profile
    history_rows: list[dict[str, Any]] = []
    weight_points_by_unit: dict[str, list[dict[str, Any]]] = {}

    for record in biometric_records_for_chart(animal):
        if record.weight_biometric_record is not None:
            sub = record.weight_biometric_record
            measurement_type, label, value, unit = "weight", "Weight", sub.weight, sub.weight_unit_to_present
        elif record.height_biometric_record is not None:
            sub = record.height_biometric_record
            measurement_type, label, value, unit = "height", "Height", sub.height, sub.height_unit_to_present
        elif record.custom_biometric_record is not None:
            sub = record.custom_biometric_record
            measurement_type, label, value, unit = "custom", sub.record_name, sub.record_value, sub.record_unit
        else:
            # No sub-type attached — shouldn't happen (validate_one_to_one_fields blocks
            # >1, create_biometric_record always sets exactly one) but don't crash on it.
            continue

        resolved_date = _resolve_biometric_date(record)
        history_rows.append(
            {
                "id": record.pk,
                "date": resolved_date,
                "measurement_type": measurement_type,
                "label": label,
                "value": value,
                "unit": unit,
                "context": record.related_note.short_description if record.related_note else "",
            }
        )

        if measurement_type == "weight":
            weight_points_by_unit.setdefault(unit, []).append(
                {"date": resolved_date.isoformat(), "value": float(value), "id": record.pk}
            )

    history_rows.sort(key=lambda row: (row["date"], row["id"]), reverse=True)

    chart_series = [
        {
            "measurement_type": "weight",
            "unit": unit,
            "label": f"Weight ({unit})",
            "points": [
                {"date": p["date"], "value": p["value"]} for p in sorted(points, key=lambda p: (p["date"], p["id"]))
            ],
        }
        for unit, points in sorted(weight_points_by_unit.items())
    ]

    return {
        "history_rows": history_rows,
        "chart_series": chart_series,
        "can_record_biometrics": user_can_record_biometrics(profile, animal),
    }


def _build_ownership(request, animal: Animal, allowed: set[str] | None = None) -> dict[str, Any]:
    return {"keepers": animal.shares.select_related("carer__user").all()}  # type: ignore


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
            frozenset({"history"}),
        ),
        Tab(
            "biometrics",
            "Biometrics",
            "animals/tabs/_biometrics.html",
            False,
            _build_biometrics,
            frozenset({"biometrics"}),
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
    deceased = animal.is_deceased

    def _tab_visible(tab: Tab) -> bool:
        # Owner-only mutation tabs (settings, ownership) are hidden for deceased animals —
        # the animal is read-only; the owner's only permitted actions are on the profile page.
        if tab.owner_only:
            return owner and not deceased
        if not tab.categories:
            return True
        return owner or bool(tab.categories & allowed)

    return {
        "now": timezone.now().date(),
        "is_owner": owner,
        "is_deceased": deceased,
        "is_pinned": is_pinned(profile, animal),
        "allowed_categories": allowed,
        "tabs": [t for t in TABS_LIST if _tab_visible(t)],
    }


class CreateAnimalView(LoginRequiredMixin, FormView):
    template_name = "animals/create.html"
    form_class = AnimalRegisterForm
    success_url = "/animals/"
    request: AuthenticatedRequest

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
    request: AuthenticatedRequest
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
        return user_can_view_animal(self.request.user.profile, animal)


class AnimalTabView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Serves individual tab content for the animal profile page.

    When called with HX-Request header (htmx): returns only the tab fragment.
    Without the header (direct navigation / JS disabled): returns the full shell
    so progressive enhancement works — every tab has a real fallback URL.
    """

    model = Animal
    context_object_name = "animal"
    request: AuthenticatedRequest

    def _get_tab(self) -> Tab:
        slug = self.kwargs.get("slug", "")
        tab = TAB_REGISTRY.get(slug)
        if tab is None:
            raise Http404(f"Unknown tab slug: {slug!r}")
        return tab

    def test_func(self):
        animal = self.get_object()
        profile = self.request.user.profile
        if not user_can_view_animal(profile, animal):
            return False
        tab = TAB_REGISTRY.get(self.kwargs.get("slug", ""))
        if tab is None:
            return True
        # Owner-only tabs (settings, ownership) are blocked on deceased animals to enforce
        # the read-only archive mode. The owner's only write actions are on the profile page.
        if tab.owner_only:
            return is_animal_owner(profile, animal) and not animal.is_deceased
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
    request: AuthenticatedRequest

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["animals"] = animals_visible_to(self.request.user.profile)
        return context


class ArchiveView(LoginRequiredMixin, TemplateView):
    """Owner-only read-only archive of deceased animals.

    Only animals owned by the current user are shown — carers are intentionally
    excluded because death withdraws management to the owner only.
    """

    template_name = "animals/archive.html"
    request: AuthenticatedRequest

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["animals"] = deceased_animals_for(self.request.user.profile)
        return context


class ToPinAnimalsView(LoginRequiredMixin, View):
    request: AuthenticatedRequest

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
