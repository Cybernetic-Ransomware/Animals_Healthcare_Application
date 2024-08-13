from animals import views as animal_views
from animals.utils_owner import views as animal_owner_views
from django.urls import path

urlpatterns = [
    path("create/", animal_views.CreateAnimalView.as_view(), name="animal_create"),
    path("<uuid:pk>/delete/", animal_owner_views.AnimalDeleteView.as_view(), name="animal_delete"),
    path("<uuid:pk>/owner/", animal_owner_views.ChangeOwnerView.as_view(), name="animal_ownership"),
    path(
        "<uuid:pk>/cnt/", animal_owner_views.ChangeFirstContactView.as_view(), name="animal_first_contact"
    ),  # TO change
    path("<uuid:pk>/btd/", animal_owner_views.ChangeBirthdayView.as_view(), name="animal_birthday"),
    path("<uuid:pk>/", animal_views.AnimalProfileDetailView.as_view(), name="animal_profile"),
    path("<uuid:pk>/upload-image/", animal_owner_views.ImageUploadView.as_view(), name="upload_image"),
    path("<uuid:pk>/manage_keepers/", animal_owner_views.ManageKeepersView.as_view(), name="manage_keepers"),
    path("animals/", animal_views.StableView.as_view(), name="animals_stable"),
    path("pinned-animals/", animal_views.ToPinAnimalsView.as_view(), name="pinned_animals"),
]
