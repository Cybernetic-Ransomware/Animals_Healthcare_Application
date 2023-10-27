from django.urls import path

# from . import views as notes_views
from medical_notes.views import type_basic_note as notes_views
from medical_notes.views import type_measurement_notes as measurement_views


urlpatterns = [
    path('<uuid:pk>/create/', notes_views.CreateNoteFormView.as_view(), name='note_create'),
    path('<uuid:pk>/edit/', notes_views.EditNoteView.as_view(), name='note_edit'),
    path('<uuid:pk>/delete/', notes_views.DeleteNoteView.as_view(), name='note_delete'),
    path('<uuid:pk>/realted/', notes_views.EditRelatedAnimalsView.as_view(), name='note_animals_edit'),

    path('<uuid:pk>/notes/', notes_views.FullTimelineOfNotes.as_view(), name='full_timeline_of_notes'),
    path('<uuid:pk>/notes/<str:tag_name>', notes_views.TagFilteredTimelineOfNotes.as_view(), name='tag_filtered_timeline_of_notes'),

    path('<uuid:pk>/<uuid:note_id>/medical_create/', measurement_views.BiometricRecordCreateView.as_view(), name='medical_create'),

]
