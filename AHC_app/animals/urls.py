from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, \
    PasswordResetConfirmView, PasswordResetCompleteView

from . import views as animal_views


urlpatterns = [
    path('animal/<int:h_pk>/', animal_views.profile, name='animal_profile'),

    path('animals/', animal_views.manager, name='animals_manage'),
    path('animal/create/', animal_views.create, name='animal_create'),

]

