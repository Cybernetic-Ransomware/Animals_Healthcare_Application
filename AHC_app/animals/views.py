import uuid

from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponseBadRequest
from django.shortcuts import render

from .models import Animal


@login_required
# @permission_required(True, login_url='homepage')  # napisz własną funkcję weryfikującym właściciela z ID zweirzęcia
def profile(request, h_pk):
    if request.method == 'GET':
        animal_id = uuid.UUID(h_pk)
        animal = Animal.objects.get(pk=animal_id)
    else:
        return HttpResponseBadRequest

    return render(request, 'animals/profile.html', {'animal': animal})
