import uuid
from datetime import date as _date
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.urls import reverse

from ahc.apps.medical_notes.models.type_feeding_notes import FeedingNote


@pytest.fixture
def existing_feeding_note(db, diet_note_shell):
    """A persisted FeedingNote linked to diet_note_shell."""
    return FeedingNote.objects.create(
        related_note=diet_note_shell,
        real_start_date=_date(2026, 1, 1),
        category="dry",
        product_name="Original Food",
    )


@pytest.mark.integration
@pytest.mark.django_db
class TestDietRecordCreateView:
    """DietRecordCreateView (feeding_create): POST creates FeedingNote and redirects."""

    def test_valid_post_creates_feeding_note(self, client, user_profile, diet_note_shell):
        user, _ = user_profile
        client.force_login(user)
        url = reverse("feeding_create", kwargs={"pk": diet_note_shell.id})
        data = {
            "real_start_date": "2026-01-01",
            "category": "dry",
            "product_name": "New Food",
            "real_end_date": "",
            "producer": "",
            "dose_annotations": "",
            "purchase_source": "",
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert FeedingNote.objects.filter(related_note=diet_note_shell).count() == 1

    def test_redirects_to_diet_list(self, client, user_profile, diet_note_shell):
        user, _ = user_profile
        client.force_login(user)
        url = reverse("feeding_create", kwargs={"pk": diet_note_shell.id})
        data = {
            "real_start_date": "2026-01-01",
            "category": "dry",
            "product_name": "New Food",
        }
        response = client.post(url, data)
        expected_redirect = reverse("note_related_diets", kwargs={"pk": str(diet_note_shell.id)})
        assert response["Location"] == expected_redirect

    def test_unauthenticated_redirects_to_login(self, client, diet_note_shell):
        url = reverse("feeding_create", kwargs={"pk": diet_note_shell.id})
        response = client.post(url, {})
        assert response.status_code == 302
        assert "/login" in response["Location"]


@pytest.mark.integration
@pytest.mark.django_db
class TestEditDietRecordView:
    """EditDietRecordView (feeding_edit): POST updates FeedingNote and redirects to diet list.

    This test asserts the CORRECTED behaviour. Against the original code the view
    returned 404 because form_valid tried to fetch an EmailNotification using the
    FeedingNote pk — a type/identity mismatch.
    """

    def test_valid_post_updates_feeding_note(self, client, user_profile, existing_feeding_note):
        user, _ = user_profile
        client.force_login(user)
        url = reverse("feeding_edit", kwargs={"pk": existing_feeding_note.pk})
        data = {
            "real_start_date": "2026-03-01",
            "category": "wet",
            "product_name": "Updated Food",
            "real_end_date": "",
            "producer": "",
            "dose_annotations": "",
            "purchase_source": "",
        }
        response = client.post(url, data)
        assert response.status_code == 302
        existing_feeding_note.refresh_from_db()
        assert existing_feeding_note.product_name == "Updated Food"

    def test_redirects_to_diet_list_of_parent_note(self, client, user_profile, existing_feeding_note):
        user, _ = user_profile
        client.force_login(user)
        url = reverse("feeding_edit", kwargs={"pk": existing_feeding_note.pk})
        data = {
            "real_start_date": "2026-03-01",
            "category": "wet",
            "product_name": "Updated Food",
        }
        response = client.post(url, data)
        expected_redirect = reverse(
            "note_related_diets",
            kwargs={"pk": str(existing_feeding_note.related_note.id)},
        )
        assert response["Location"] == expected_redirect


@pytest.mark.integration
@pytest.mark.django_db
class TestFeedingNoteListViewAccess:
    """FeedingNoteListView (note_related_diets): permission mixin enforced after refactor."""

    def test_owner_can_access(self, client, user_profile, diet_note_shell):
        user, _ = user_profile
        client.force_login(user)
        url = reverse("note_related_diets", kwargs={"pk": diet_note_shell.id})
        response = client.get(url)
        assert response.status_code == 200

    def test_stranger_is_denied(self, client, second_user_profile, diet_note_shell):
        stranger, _ = second_user_profile
        client.force_login(stranger)
        url = reverse("note_related_diets", kwargs={"pk": diet_note_shell.id})
        response = client.get(url)
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.django_db
class TestNotificationListEmptyState:
    """Regression for D-03: notification_list.html must show an empty state, not a blank page."""

    def test_shows_empty_state_when_no_notifications(self, client, user_profile):
        user, _ = user_profile
        client.force_login(user)

        response = client.get(reverse("note_related_notifications"), {"mednote_uuid": str(uuid.uuid4())})

        assert response.status_code == 200
        assert b"No notifications set for this record yet." in response.content

    def test_shows_notifications_when_present(self, client, user_profile, diet_note_shell):
        """Stubs the queryset — EmailNotification.days_of_week (ArrayField) can't be written via SQLite."""
        user, _ = user_profile
        fake_notification = SimpleNamespace(
            pk=1,
            description="Feed reminder",
            is_active=True,
            daily_timestamp=None,
            timezone="Europe/London",
            start_date=_date(2026, 1, 1),
            end_date=None,
            days_of_week=[False] * 7,
            receiver_name="Owner",
            message="Time to feed",
            last_modification=None,
        )
        client.force_login(user)

        with patch(
            "ahc.apps.medical_notes.views.type_feeding_notes.notifications_for_mednote",
            return_value=[fake_notification],
        ):
            response = client.get(reverse("note_related_notifications"), {"mednote_uuid": str(diet_note_shell.id)})

        assert response.status_code == 200
        assert b"No notifications set for this record yet." not in response.content
        assert b"Feed reminder" in response.content
