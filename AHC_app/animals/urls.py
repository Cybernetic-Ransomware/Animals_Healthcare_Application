from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, \
    PasswordResetConfirmView, PasswordResetCompleteView

from . import views as animal_views

urlpatterns = [
    path('animal/create/', animal_views.CreateFormView.as_view(), name='animal_create'),
    path('animal/<uuid:pk>/delete/', animal_views.AnimalDeleteView.as_view(), name='animal_delete'),
    path('animal/<uuid:pk>/owner/', animal_views.ChangeOwnerView.as_view(), name='animal_ownership'),

    path('animal/<uuid:pk>/cnt/', animal_views.AnimalProfileDetailView.as_view(), name='animal_first_contact'),  # TO change
    path('animal/<uuid:pk>/btd/', animal_views.ChangeBirthdayView.as_view(), name='animal_birthday'),

    path('animal/<uuid:pk>/', animal_views.AnimalProfileDetailView.as_view(), name='animal_profile'),
    path('animal/<uuid:pk>/upload-image/', animal_views.ImageUploadView.as_view(), name='upload_image'),
    path('animal/<uuid:pk>/manage_keepers/', animal_views.ManageKeepersView.as_view(), name='manage_keepers'),

    path('animals/', animal_views.StableView.as_view(), name='animals_stable'),

]
