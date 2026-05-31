from django.urls import path

from ahc.apps.animals import views as animal_views
from ahc.apps.animals.utils_owner import views as animal_owner_views

urlpatterns = [
    path("create/", animal_views.CreateAnimalView.as_view(), name="animal_create"),
    path("<uuid:pk>/delete/", animal_owner_views.AnimalDeleteView.as_view(), name="animal_delete"),
    path("<uuid:pk>/owner/", animal_owner_views.ChangeOwnerView.as_view(), name="animal_ownership"),
    path("<uuid:pk>/cnt/", animal_owner_views.ChangeFirstContactView.as_view(), name="animal_first_contact"),  # TO change
    path("<uuid:pk>/btd/", animal_owner_views.ChangeBirthdayView.as_view(), name="animal_birthday"),
    path("<uuid:pk>/", animal_views.AnimalProfileDetailView.as_view(), name="animal_profile"),
    path("<uuid:pk>/tab/<slug:slug>/", animal_views.AnimalTabView.as_view(), name="animal_tab"),
    path("<uuid:pk>/upload-image/", animal_owner_views.ImageUploadView.as_view(), name="upload_image"),
    path("<uuid:pk>/manage_keepers/", animal_owner_views.ManageKeepersView.as_view(), name="manage_keepers"),
    path("<uuid:pk>/next-visit/", animal_owner_views.ChangeNextVisitView.as_view(), name="animal_next_visit"),
    path(
        "<uuid:pk>/dietary-restrictions/",
        animal_owner_views.ChangeDietaryRestrictionsView.as_view(),
        name="animal_dietary_restrictions",
    ),
    path("<uuid:pk>/details/", animal_owner_views.ChangeAnimalDetailsView.as_view(), name="animal_details"),
    path("<uuid:pk>/keepers/<int:keeper_pk>/remove/", animal_owner_views.RemoveKeeperView.as_view(), name="remove_keeper"),
    path("animals/", animal_views.StableView.as_view(), name="animals_stable"),
    path("pinned-animals/", animal_views.ToPinAnimalsView.as_view(), name="pinned_animals"),
]
