import uuid

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView

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


class AnimalProfileDetailView(LoginRequiredMixin, DetailView):
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
        return context


@login_required
# @permission_required(True, login_url='homepage')  # napisz własną funkcję weryfikującym właściciela z ID zweirzęcia
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


class ImageUploadView(LoginRequiredMixin, FormView):
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

        animal_id = self.kwargs["pk"]

        self.success_url = reverse("animal_profile", kwargs={"pk": animal_id})
        return redirect(self.success_url)
