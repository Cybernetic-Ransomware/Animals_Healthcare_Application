from animals.mixins.animal_owner_permissions import UserPassesOwnershipTestMixin
from animals.models import Animal
from animals.utils_owner.forms import (
    ChangeBirthdayForm,
    ChangeFirstContactForm,
    ChangeOwnerForm,
    ImageUploadForm,
    ManageKeepersForm,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import DeleteView
from django.views.generic.edit import FormView
from PIL import Image


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

        animal_instance = form.instance
        img = Image.open(animal_instance.profile_image.path)

        if img.height > 448 or img.width > 448:
            output_size = (448, 448)
            img.thumbnail(output_size)
            img.save(animal_instance.profile_image.path)

        success_url = reverse("animal_profile", kwargs={"pk": animal_instance.pk})
        return redirect(success_url)


class ChangeOwnerView(LoginRequiredMixin, UserPassesOwnershipTestMixin, FormView):
    template_name = "animals/change_owner.html"
    form_class = ChangeOwnerForm

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
        animal = form.instance
        new_owner = form.cleaned_data["new_owner"]
        set_keeper = form.cleaned_data["set_keeper"]
        animal.owner = new_owner
        animal.save()

        if set_keeper:
            animal.allowed_users.add(self.request.user.profile)

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
        context["allowed_users"] = animal.allowed_users.all()
        context["animal_url"] = reverse("animal_profile", kwargs={"pk": self.get_form().instance.id})
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = Animal.objects.get(pk=self.kwargs["pk"])
        return kwargs

    def form_valid(self, form):
        animal = form.instance
        new_keeper = form.cleaned_data["input_user"]

        animal.allowed_users.add(new_keeper)
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
        animal = get_object_or_404(Animal, pk=self.kwargs["pk"])
        animal.birthdate = form.cleaned_data["birthdate"]
        animal.save()

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
        animal = get_object_or_404(Animal, pk=self.kwargs["pk"])
        animal.first_contact_vet = form.cleaned_data["first_contact_vet"]
        animal.first_contact_medical_place = form.cleaned_data["first_contact_medical_place"]
        animal.save()
        return super().form_valid(form)

    def get_success_url(self):
        return self.request.path
