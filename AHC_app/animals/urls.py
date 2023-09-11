from django.urls import path

from . import views as animal_views


urlpatterns = [
    path('create/', animal_views.CreateAnimalView.as_view(), name='animal_create'),
    path('<uuid:pk>/delete/', animal_views.AnimalDeleteView.as_view(), name='animal_delete'),
    path('<uuid:pk>/owner/', animal_views.ChangeOwnerView.as_view(), name='animal_ownership'),

    path('<uuid:pk>/cnt/', animal_views.ChangeFirstContactView.as_view(), name='animal_first_contact'),  # TO change
    path('<uuid:pk>/btd/', animal_views.ChangeBirthdayView.as_view(), name='animal_birthday'),

    path('<uuid:pk>/', animal_views.AnimalProfileDetailView.as_view(), name='animal_profile'),
    path('<uuid:pk>/upload-image/', animal_views.ImageUploadView.as_view(), name='upload_image'),
    path('<uuid:pk>/manage_keepers/', animal_views.ManageKeepersView.as_view(), name='manage_keepers'),

    path('animals/', animal_views.StableView.as_view(), name='animals_stable'),

]
