from django.urls import path

from ahc.apps.veterinary import views

urlpatterns = [
    path("contacts/", views.ContactBookView.as_view(), name="contact_book"),
    path("contacts/vets/new/", views.VetCreateView.as_view(), name="vet_create"),
    path("contacts/vets/<uuid:pk>/edit/", views.VetUpdateView.as_view(), name="vet_edit"),
    path("contacts/vets/<uuid:pk>/delete/", views.VetDeleteView.as_view(), name="vet_delete"),
    path("contacts/places/new/", views.MedicalPlaceCreateView.as_view(), name="medical_place_create"),
    path("contacts/places/<uuid:pk>/edit/", views.MedicalPlaceUpdateView.as_view(), name="medical_place_edit"),
    path("contacts/places/<uuid:pk>/delete/", views.MedicalPlaceDeleteView.as_view(), name="medical_place_delete"),
]
