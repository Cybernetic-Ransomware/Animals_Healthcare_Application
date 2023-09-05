from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView

from .forms import AnimalRegisterForm
from .models import Animal
from .owner_utils.views import AnimalDeleteView, ImageUploadView, ChangeOwnerView, ManageKeepersView, ChangeBirthdayView


class CreateFormView(LoginRequiredMixin, FormView):
    template_name = "animals/create.html"
    form_class = AnimalRegisterForm
    success_url = "/animals/"

    def form_valid(self, form):
        new_animal = form.save(commit=False)
        new_animal.owner = self.request.user.profile
        new_animal.save()

        self.success_url = reverse("animal_profile", kwargs={"pk": new_animal.id})

        return super().form_valid(form)


class AnimalProfileDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Animal
    template_name = "animals/profile.html"
    context_object_name = "animal"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['now'] = timezone.now().date()

        # only for visibility of buttons, do not use as authentication
        context["is_owner"] = self.object.owner == self.request.user.profile

        return context

    def test_func(self):
        all_users = set(self.get_object().allowed_users.all())
        all_users.add(self.get_object().owner)

        user = self.request.user.profile

        return user in all_users


class StableView(TemplateView, LoginRequiredMixin):
    template_name = "animals/all_animals_stable.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        query = Animal.objects.filter(
            Q(owner=self.request.user.profile)
            | Q(allowed_users=self.request.user.profile)
        ).order_by("-creation_date")

        context["animals"] = query

        return context
