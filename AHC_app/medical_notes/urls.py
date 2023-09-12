from django.urls import path

from . import views as notes_views


urlpatterns = [
    path('<uuid:pk>/create/', notes_views.CreateNoteFormView.as_view(), name='note_create'),
    # path('<uuid:pk>/delete/', notes_views.AnimalDeleteView.as_view(), name='note_delete'),

]
