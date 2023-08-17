from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, \
    PasswordResetConfirmView, PasswordResetCompleteView

from . import views as animal_views


urlpatterns = [
    path('animal/<uuid:pk>/', animal_views.AnimalProfileDetailView.as_view(), name='animal_profile'),
    path('animal/<uuid:pk>/upload-image/', animal_views.ImageUploadView.as_view(), name='upload_image'),

    path('animals/', animal_views.stable, name='animals_stable'),
    path('animal/create/', animal_views.CreateFormView.as_view(), name='animal_create'),

]
