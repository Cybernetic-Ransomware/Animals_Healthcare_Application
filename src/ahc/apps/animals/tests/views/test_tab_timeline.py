import html
import re
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from ahc.apps.animals.models import Animal


@pytest.mark.integration
@pytest.mark.django_db
class TestTimelineLoadMorePagination:
    """Regression for the "+HH:MM" cursor offset decoded as a space, making parse_datetime() return None."""

    @pytest.fixture
    def animal(self, db, user_profile):
        _, profile = user_profile
        return Animal.objects.create(full_name="Milo", owner=profile)

    def _create_records(self, animal, profile, count, type_of_event):
        """Create `count` MedicalRecords, newest-first, backdated via .update() (auto_now_add ignores explicit values)."""
        from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord

        base = timezone.now()
        created = [
            MedicalRecord.objects.create(
                animal=animal, author=profile, short_description=f"{type_of_event} {i}", type_of_event=type_of_event
            )
            for i in range(count)
        ]
        for i, record in enumerate(created):
            MedicalRecord.objects.filter(pk=record.pk).update(date_creation=base - timedelta(hours=i))
        return list(MedicalRecord.objects.filter(pk__in=[r.pk for r in created]).order_by("-date_creation"))

    def _create_notes(self, animal, profile, count):
        return self._create_records(animal, profile, count, "fast_note")

    def _create_vet_visits(self, animal, profile, count):
        return self._create_records(animal, profile, count, "medical_visit")

    def _present_pks(self, content, records):
        return {r.pk for r in records if reverse("note_edit", kwargs={"pk": r.pk}) in content}

    def _has_load_more(self, content, node_id):
        return f'id="{node_id}"' in content

    def _extract_load_more_href(self, content, node_id):
        """Extract the rendered hx-get URL, HTML-unescaped like a browser, for replaying the same encoding path."""
        match = re.search(rf'id="{node_id}"[\s\S]*?hx-get="([^"]+)"', content)
        assert match, f"expected a Load older node with id={node_id!r} in response"
        return html.unescape(match.group(1))

    def test_notes_20_records_renders_all_without_load_more(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        records = self._create_notes(animal, profile, 20)
        c = logged_in_client(user)

        response = c.get(f"/pet/{animal.id}/tab/notes/", HTTP_HX_REQUEST="true")
        content = response.content.decode()

        assert self._present_pks(content, records) == {r.pk for r in records}
        assert not self._has_load_more(content, "timeline-more-notes")

    def test_notes_21_records_second_page_has_exactly_one_new_record(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        records = self._create_notes(animal, profile, 21)
        c = logged_in_client(user)

        first_content = c.get(f"/pet/{animal.id}/tab/notes/", HTTP_HX_REQUEST="true").content.decode()
        first_present = self._present_pks(first_content, records)
        assert len(first_present) == 20
        assert self._has_load_more(first_content, "timeline-more-notes")

        href = self._extract_load_more_href(first_content, "timeline-more-notes")
        second_content = c.get(href, HTTP_HX_REQUEST="true").content.decode()
        second_present = self._present_pks(second_content, records)

        assert len(second_present) == 1
        assert first_present.isdisjoint(second_present)
        assert first_present | second_present == {r.pk for r in records}
        assert not self._has_load_more(second_content, "timeline-more-notes")

    def test_notes_24_records_second_page_has_remaining_four_no_duplicates(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        records = self._create_notes(animal, profile, 24)
        c = logged_in_client(user)

        first_content = c.get(f"/pet/{animal.id}/tab/notes/", HTTP_HX_REQUEST="true").content.decode()
        first_present = self._present_pks(first_content, records)
        assert len(first_present) == 20
        assert self._has_load_more(first_content, "timeline-more-notes")

        href = self._extract_load_more_href(first_content, "timeline-more-notes")
        second_content = c.get(href, HTTP_HX_REQUEST="true").content.decode()
        second_present = self._present_pks(second_content, records)

        assert len(second_present) == 4
        assert first_present.isdisjoint(second_present)
        assert first_present | second_present == {r.pk for r in records}
        assert not self._has_load_more(second_content, "timeline-more-notes")

    def test_notes_40_records_two_full_pages_no_load_more_after(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        records = self._create_notes(animal, profile, 40)
        c = logged_in_client(user)

        first_content = c.get(f"/pet/{animal.id}/tab/notes/", HTTP_HX_REQUEST="true").content.decode()
        first_present = self._present_pks(first_content, records)
        assert len(first_present) == 20
        assert self._has_load_more(first_content, "timeline-more-notes")

        href = self._extract_load_more_href(first_content, "timeline-more-notes")
        second_content = c.get(href, HTTP_HX_REQUEST="true").content.decode()
        second_present = self._present_pks(second_content, records)

        assert len(second_present) == 20
        assert first_present.isdisjoint(second_present)
        assert first_present | second_present == {r.pk for r in records}
        assert not self._has_load_more(second_content, "timeline-more-notes")

    def test_notes_41_records_three_pages_each_record_appears_once(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        records = self._create_notes(animal, profile, 41)
        c = logged_in_client(user)

        first_content = c.get(f"/pet/{animal.id}/tab/notes/", HTTP_HX_REQUEST="true").content.decode()
        first_present = self._present_pks(first_content, records)
        assert len(first_present) == 20
        assert self._has_load_more(first_content, "timeline-more-notes")

        href = self._extract_load_more_href(first_content, "timeline-more-notes")
        second_content = c.get(href, HTTP_HX_REQUEST="true").content.decode()
        second_present = self._present_pks(second_content, records)
        assert len(second_present) == 20
        assert self._has_load_more(second_content, "timeline-more-notes")

        href2 = self._extract_load_more_href(second_content, "timeline-more-notes")
        third_content = c.get(href2, HTTP_HX_REQUEST="true").content.decode()
        third_present = self._present_pks(third_content, records)
        assert len(third_present) == 1
        assert not self._has_load_more(third_content, "timeline-more-notes")

        assert first_present.isdisjoint(second_present)
        assert first_present.isdisjoint(third_present)
        assert second_present.isdisjoint(third_present)
        assert first_present | second_present | third_present == {r.pk for r in records}

    def test_vet_24_records_second_page_has_remaining_four_no_duplicates(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        records = self._create_vet_visits(animal, profile, 24)
        c = logged_in_client(user)

        first_content = c.get(f"/pet/{animal.id}/tab/vet/", HTTP_HX_REQUEST="true").content.decode()
        first_present = self._present_pks(first_content, records)
        assert len(first_present) == 20
        assert self._has_load_more(first_content, "timeline-more-vet")

        href = self._extract_load_more_href(first_content, "timeline-more-vet")
        second_content = c.get(href, HTTP_HX_REQUEST="true").content.decode()
        second_present = self._present_pks(second_content, records)

        assert len(second_present) == 4
        assert first_present.isdisjoint(second_present)
        assert first_present | second_present == {r.pk for r in records}
        assert not self._has_load_more(second_content, "timeline-more-vet")

    def test_notes_month_jump_then_load_older_continues_without_duplicates(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        records = self._create_notes(animal, profile, 25)
        month_param = records[0].date_creation.strftime("%Y-%m")
        c = logged_in_client(user)

        first_response = c.get(f"/pet/{animal.id}/tab/notes/?month={month_param}", HTTP_HX_REQUEST="true")
        assert first_response.status_code == 200
        first_content = first_response.content.decode()
        first_present = self._present_pks(first_content, records)
        assert len(first_present) == 20
        assert self._has_load_more(first_content, "timeline-more-notes")

        href = self._extract_load_more_href(first_content, "timeline-more-notes")
        assert "month=" not in href, "Load older must continue from the cursor, not re-target the whole month"

        second_content = c.get(href, HTTP_HX_REQUEST="true").content.decode()
        second_present = self._present_pks(second_content, records)

        assert len(second_present) == 5
        assert first_present.isdisjoint(second_present)
        assert first_present | second_present == {r.pk for r in records}
        assert not self._has_load_more(second_content, "timeline-more-notes")

    def test_notes_malformed_cursor_fails_closed(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        records = self._create_notes(animal, profile, 24)
        c = logged_in_client(user)

        response = c.get(f"/pet/{animal.id}/tab/notes/?before=not-a-datetime&load_more=1", HTTP_HX_REQUEST="true")
        content = response.content.decode()

        assert response.status_code == 200
        assert self._present_pks(content, records) == set()
        assert not self._has_load_more(content, "timeline-more-notes")

    def test_notes_before_without_before_id_fails_closed(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        records = self._create_notes(animal, profile, 24)
        c = logged_in_client(user)

        first_content = c.get(f"/pet/{animal.id}/tab/notes/", HTTP_HX_REQUEST="true").content.decode()
        href = self._extract_load_more_href(first_content, "timeline-more-notes")
        before_only = href.split("&before_id=")[0]

        response = c.get(f"{before_only}&load_more=1", HTTP_HX_REQUEST="true")
        content = response.content.decode()

        assert response.status_code == 200
        assert self._present_pks(content, records) == set()
        assert not self._has_load_more(content, "timeline-more-notes")

    def test_notes_tied_date_creation_at_page_boundary_drops_no_records(self, animal, user_profile, logged_in_client):
        from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord

        user, profile = user_profile
        base = timezone.now()

        unique = [
            MedicalRecord.objects.create(
                animal=animal, author=profile, short_description=f"unique {i}", type_of_event="fast_note"
            )
            for i in range(19)
        ]
        for i, r in enumerate(unique):
            MedicalRecord.objects.filter(pk=r.pk).update(date_creation=base - timedelta(hours=i + 1))

        # 5 records sharing one timestamp, straddling the page boundary (1 of them fills page one).
        tied_ts = base - timedelta(hours=20)
        tied = [
            MedicalRecord.objects.create(
                animal=animal, author=profile, short_description=f"tied {i}", type_of_event="fast_note"
            )
            for i in range(5)
        ]
        for r in tied:
            MedicalRecord.objects.filter(pk=r.pk).update(date_creation=tied_ts)

        records = list(MedicalRecord.objects.filter(pk__in=[r.pk for r in unique + tied]))
        c = logged_in_client(user)

        first_content = c.get(f"/pet/{animal.id}/tab/notes/", HTTP_HX_REQUEST="true").content.decode()
        first_present = self._present_pks(first_content, records)
        assert len(first_present) == 20
        assert self._has_load_more(first_content, "timeline-more-notes")

        href = self._extract_load_more_href(first_content, "timeline-more-notes")
        second_content = c.get(href, HTTP_HX_REQUEST="true").content.decode()
        second_present = self._present_pks(second_content, records)

        assert len(second_present) == 4
        assert first_present.isdisjoint(second_present)
        assert first_present | second_present == {r.pk for r in records}
        assert not self._has_load_more(second_content, "timeline-more-notes")

    def test_notes_load_more_href_survives_url_round_trip_with_tz_offset_cursor(
        self, animal, user_profile, logged_in_client
    ):
        """Cursor is always UTC ("+00:00"); href must carry a percent-encoded '+' or this test passes vacuously."""
        user, profile = user_profile
        records = self._create_notes(animal, profile, 21)
        c = logged_in_client(user)

        first_content = c.get(f"/pet/{animal.id}/tab/notes/", HTTP_HX_REQUEST="true").content.decode()
        href = self._extract_load_more_href(first_content, "timeline-more-notes")
        cursor_value = href.split("before=")[1].split("&")[0]

        assert "%2B" in cursor_value, f"expected a percent-encoded '+' UTC offset in the cursor, got {cursor_value!r}"
        assert "+" not in cursor_value, "a literal '+' would be decoded as a space by the server"

        second_content = c.get(href, HTTP_HX_REQUEST="true").content.decode()
        second_present = self._present_pks(second_content, records)

        assert len(second_present) == 1
        assert not self._has_load_more(second_content, "timeline-more-notes")
