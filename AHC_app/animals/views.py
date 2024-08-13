from animals.forms import AnimalRegisterForm, PinAnimalForm
from animals.models import Animal
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView, View
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView
from medical_notes.models.type_basic_note import MedicalRecord

# from users.models import Profile as UserProfile


class CreateAnimalView(LoginRequiredMixin, FormView):
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
        context["now"] = timezone.now().date()

        # only for visibility of buttons, do not use as authentication
        context["is_owner"] = self.object.owner == self.request.user.profile

        context["is_pinned"] = context["is_pinned"] = self.request.user.profile.pinned_animals.filter(
            pk=self.object.pk
        ).exists()

        recent_records = MedicalRecord.objects.filter(animal=self.object).order_by("-date_creation")[:5]

        context["recent_records"] = recent_records

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
            Q(owner=self.request.user.profile) | Q(allowed_users=self.request.user.profile)
        ).order_by("-creation_date")

        context["animals"] = query

        return context


class ToPinAnimalsView(View):
    def post(self, request, *args, **kwargs):
        print("DUPA1")

        form = PinAnimalForm(request.POST)
        print(form)

        current_user = request.user

        if form.is_valid():
            animal_id = form.cleaned_data["animal_id"]
            action = form.cleaned_data["action"]

            if action == "add":
                animal = Animal.objects.get(id=animal_id)
                current_user.pinned_animals.add(animal)
                current_user.save()
            elif action == "remove":
                current_user.pinned_animals.remove(animal_id)
                current_user.save()

        return JsonResponse({"status": "success"})
