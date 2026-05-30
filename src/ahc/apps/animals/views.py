from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
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
    recent_records_for,
    user_can_access_animal,
)
from ahc.apps.animals.services import create_animal, pin_animal, unpin_animal


class CreateAnimalView(LoginRequiredMixin, FormView):
    template_name = "animals/create.html"
    form_class = AnimalRegisterForm
    success_url = "/animals/"

    def form_valid(self, form):
        new_animal = create_animal(self.request.user.profile, form)
        self.success_url = reverse("animal_profile", kwargs={"pk": new_animal.id})
        return super().form_valid(form)


class AnimalProfileDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Animal
    template_name = "animals/profile.html"
    context_object_name = "animal"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.profile
        context["now"] = timezone.now().date()
        # only for button visibility, do not use as authentication
        context["is_owner"] = is_animal_owner(profile, self.object)
        context["is_pinned"] = is_pinned(profile, self.object)
        context["recent_records"] = recent_records_for(self.object)
        return context

    def test_func(self):
        animal = self.get_object()
        return user_can_access_animal(self.request.user.profile, animal)


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
