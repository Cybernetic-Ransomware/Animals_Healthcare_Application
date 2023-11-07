from django.urls import path

# from . import views as notes_views
from medical_notes.views import type_basic_note as notes_views
from medical_notes.views import type_feeding_notes as feeding_views
from medical_notes.views import type_measurement_notes as measurement_views


urlpatterns = [
    path('<uuid:pk>/create/', notes_views.CreateNoteFormView.as_view(), name='note_create'),
    path('<uuid:pk>/edit/', notes_views.EditNoteView.as_view(), name='note_edit'),
    path('<uuid:pk>/delete/', notes_views.DeleteNoteView.as_view(), name='note_delete'),
    path('<uuid:pk>/realted/', notes_views.EditRelatedAnimalsView.as_view(), name='note_animals_edit'),

    path('<uuid:pk>/notes/', notes_views.FullTimelineOfNotes.as_view(), name='full_timeline_of_notes'),

    path('<uuid:pk>/<uuid:note_id>/feeding_create/', feeding_views.DietRecordCreateView.as_view(), name='feeding_create'),
    path('<uuid:pk>/feeding_edit/', feeding_views.EditDietRecordView.as_view(), name='feeding_edit'),
    path('<uuid:pk>/notify_create/', feeding_views.CreateNotificationView.as_view(), name='notification_create'),

    path('<uuid:pk>/<uuid:note_id>/medical_create/', measurement_views.BiometricRecordCreateView.as_view(), name='biometric_create'),

]
