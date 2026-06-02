from django.urls import path

from ahc.apps.medical_notes.views import type_basic_note as notes_views
from ahc.apps.medical_notes.views import type_feeding_notes as feeding_views
from ahc.apps.medical_notes.views import type_measurement_notes as measurement_views
from ahc.apps.medical_notes.views import type_vaccination_notes as vaccination_views

urlpatterns = [
    path("<uuid:pk>/create/", notes_views.CreateNoteFormView.as_view(), name="note_create"),
    path("<uuid:pk>/edit/", notes_views.EditNoteView.as_view(), name="note_edit"),
    path("<uuid:pk>/delete/", notes_views.DeleteNoteView.as_view(), name="note_delete"),
    path("<uuid:pk>/related/", notes_views.EditRelatedAnimalsView.as_view(), name="note_animals_edit"),
    path("<uuid:pk>/notes/", notes_views.FullTimelineOfNotes.as_view(), name="full_timeline_of_notes"),
    path("<uuid:pk>/feeding_create/", feeding_views.DietRecordCreateView.as_view(), name="feeding_create"),
    path("<pk>/feeding_edit/", feeding_views.EditDietRecordView.as_view(), name="feeding_edit"),
    path("<uuid:pk>/diet_list/", feeding_views.FeedingNoteListView.as_view(), name="note_related_diets"),
    path("<pk>/notify_create/", feeding_views.CreateNotificationView.as_view(), name="notification_create"),
    path("<pk>/notify_active/", feeding_views.NotificationListView.as_view(), name="notification_change_active"),
    path("<pk>/notify_delete/", feeding_views.NotificationListView.as_view(), name="notification_delete"),
    path("notifications/", feeding_views.NotificationListView.as_view(), name="note_related_notifications"),
    path(
        "<uuid:pk>/<uuid:note_id>/medical_create/",
        measurement_views.BiometricRecordCreateView.as_view(),
        name="biometric_create",
    ),
    path("<pk>/attachment_edit/", notes_views.EditMedicalRecordAttachmentDescription.as_view(), name="attachment_edit"),
    path("<pk>/attachment_delete/", notes_views.DeleteMedicalRecordAttachment.as_view(), name="attachment_delete"),
    path(
        "<str:id>/<str:name>/attachment_download/",
        notes_views.DownloadAttachmentView.as_view(),
        name="attachment_download",
    ),
    path("<uuid:pk>/vaccination/add/", vaccination_views.VaccinationAddView.as_view(), name="vaccination_add"),
    path("<uuid:vacc_id>/vaccination/edit/", vaccination_views.VaccinationEditView.as_view(), name="vaccination_edit"),
    path("<uuid:vacc_id>/vaccination/save/", vaccination_views.VaccinationSaveView.as_view(), name="vaccination_save"),
    path(
        "<uuid:vacc_id>/vaccination/cancel/",
        vaccination_views.VaccinationCancelView.as_view(),
        name="vaccination_cancel",
    ),
    path(
        "<uuid:vacc_id>/vaccination/delete/",
        vaccination_views.VaccinationDeleteView.as_view(),
        name="vaccination_delete",
    ),
]
