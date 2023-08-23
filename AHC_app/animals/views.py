import uuid

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import DeleteView
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView
from PIL import Image

from .forms import AnimalRegisterForm, ImageUploadForm
from .models import Animal


@login_required
# @permission_required(True, login_url='homepage')  # napisz własną funkcję weryfikującym właściciela z ID zweirzęcia
def profile(request, h_pk):
    if request.method == "GET":
        animal_id = uuid.UUID(h_pk)
        animal = Animal.objects.get(pk=animal_id)
    else:
        return HttpResponseNotAllowed("405 Method Not Allowed")

    return render(request, "animals/profile.html", {"animal": animal})


class AnimalProfileDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Animal
    template_name = "animals/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["animal"] = self.object
        context["name"] = self.object.owner
        context["image"] = self.object.profile_image.url
        context["upload_image_url"] = reverse(
            "upload_image", kwargs={"pk": self.object.id}
        )
        context["animal_delete_url"] = reverse(
            "animal_delete", kwargs={"pk": self.object.id}
        )
        # only for visibility of buttons, do not use as authentication
        context["is_owner"] = self.object.owner == self.get_object().owner

        return context

    def test_func(self):
        all_users = set(self.get_object().allowed_users.all())
        all_users.add(self.get_object().owner)

        user = self.request.user.profile

        return user in all_users


@login_required
def stable(request):
    if request.method == "GET":
        return HttpResponse("501 Not Implemented: site in build")
    else:
        return HttpResponse("501 Not Implemented: site in build")

    # return render(request, 'animals/profile.html', {})


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


class ImageUploadView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = "animals/image.html"
    form_class = ImageUploadForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["animal_id"] = self.kwargs["pk"]
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        animal_id = self.kwargs["pk"]
        kwargs["instance"] = Animal.objects.get(id=animal_id)
        return kwargs

    def form_valid(self, form):
        form.save()

        animal_instance = form.instance
        img = Image.open(animal_instance.profile_image.path)

        if any([img.height > 300, img.width > 300]):
            output_size = (448, 448)
            img.thumbnail(output_size)
            img.save(animal_instance.profile_image.path)

        self.success_url = reverse("animal_profile", kwargs={"pk": animal_instance.pk})
        return redirect(self.success_url)

    def test_func(self):
        owner = Animal.objects.get(pk=self.kwargs['pk']).owner
        user = self.request.user.profile

        return user == owner


class AnimalDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Animal
    template_name = "animals/animal_confirm_delete.html"
    success_url = reverse_lazy("Homepage")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["animal_id"] = self.kwargs["pk"]
        return context

    def test_func(self):
        owner = Animal.objects.get(pk=self.kwargs['pk']).owner
        user = self.request.user.profile

        return user == owner
