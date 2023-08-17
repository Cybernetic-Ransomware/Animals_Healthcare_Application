import uuid

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import FormView
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseBadRequest, HttpResponseNotAllowed
from django.shortcuts import render, redirect

from .forms import AnimalRegisterForm
from .models import Animal


@login_required
# @permission_required(True, login_url='homepage')  # napisz własną funkcję weryfikującym właściciela z ID zweirzęcia
def profile(request, h_pk):
    if request.method == 'GET':
        animal_id = uuid.UUID(h_pk)
        animal = Animal.objects.get(pk=animal_id)
    else:
        return HttpResponseNotAllowed("405 Method Not Allowed")

    return render(request, 'animals/profile.html', {'animal': animal})


@login_required
# @permission_required(True, login_url='homepage')  # napisz własną funkcję weryfikującym właściciela z ID zweirzęcia
def stable(request):
    if request.method == 'GET':
        return HttpResponse("501 Not Implemented: site in build")
    else:
        return HttpResponse("501 Not Implemented: site in build")

    return render(request, 'animals/profile.html', {})


class CreateFormView(LoginRequiredMixin, FormView):
    template_name = "animals/create.html"
    form_class = AnimalRegisterForm
    success_url = "/animals/"

    def form_valid(self, form):
        new_animal = form.save(commit=False)
        new_animal.owner = self.request.user.profile
        new_animal.save()
        return super().form_valid(form)
