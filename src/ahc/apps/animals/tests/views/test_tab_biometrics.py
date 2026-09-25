from datetime import date

import pytest
from django.utils import timezone

from ahc.apps.animals.models import Animal


@pytest.mark.integration
@pytest.mark.django_db
class TestBiometricsTabAccess:
    """Biometrics tab (slug='biometrics'): visibility and access control.

    Mirrors TestAnimalTabView's pattern; covers the category split introduced when
    biometrics was pulled out of the Notes tab into its own tab (Notes now only gates
    on "history").
    """

    @pytest.fixture
    def animal(self, db, user_profile):
        _, profile = user_profile
        return Animal.objects.create(full_name="Luna", owner=profile)

    def test_owner_sees_biometrics_tab_and_can_open_it(self, animal, user_profile, logged_in_client):
        user, _ = user_profile
        c = logged_in_client(user)
        response = c.get(f"/pet/{animal.id}/")
        slugs = {t.slug for t in response.context["tabs"]}
        assert "biometrics" in slugs

        response = c.get(f"/pet/{animal.id}/tab/biometrics/", HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        assert response.context["can_record_biometrics"] is True

    def test_keeper_with_allow_biometrics_sees_tab(self, animal, second_user_profile, logged_in_client):
        from ahc.apps.animals.models import AnimalShare

        carer_user, carer_profile = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer_profile, allow_biometrics=True)
        c = logged_in_client(carer_user)
        response = c.get(f"/pet/{animal.id}/tab/biometrics/", HTTP_HX_REQUEST="true")
        assert response.status_code == 200

    def test_keeper_without_allow_biometrics_blocked(self, animal, second_user_profile, logged_in_client):
        from ahc.apps.animals.models import AnimalShare

        carer_user, carer_profile = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer_profile, allow_biometrics=False)
        c = logged_in_client(carer_user)
        response = c.get(f"/pet/{animal.id}/tab/biometrics/", HTTP_HX_REQUEST="true")
        assert response.status_code == 403

    def test_expired_share_blocked(self, animal, second_user_profile, logged_in_client):
        from ahc.apps.animals.models import AnimalShare

        carer_user, carer_profile = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer_profile, allow_biometrics=True, valid_until=date(2020, 1, 1))
        c = logged_in_client(carer_user)
        response = c.get(f"/pet/{animal.id}/tab/biometrics/", HTTP_HX_REQUEST="true")
        assert response.status_code == 403

    def test_deceased_owner_sees_history_but_no_actions(self, user_profile, logged_in_client):
        user, profile = user_profile
        deceased = Animal.objects.create(full_name="Passed", owner=profile, date_of_death=date(2024, 3, 15))
        c = logged_in_client(user)
        response = c.get(f"/pet/{deceased.id}/tab/biometrics/", HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        assert response.context["can_record_biometrics"] is False
        assert "Add measurement" not in response.content.decode()

    def test_keeper_only_history_does_not_see_biometrics(self, animal, second_user_profile, logged_in_client):
        from ahc.apps.animals.models import AnimalShare

        carer_user, carer_profile = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer_profile, allow_history=True, allow_biometrics=False)
        c = logged_in_client(carer_user)
        assert c.get(f"/pet/{animal.id}/tab/notes/", HTTP_HX_REQUEST="true").status_code == 200
        assert c.get(f"/pet/{animal.id}/tab/biometrics/", HTTP_HX_REQUEST="true").status_code == 403

    def test_keeper_only_biometrics_does_not_see_notes(self, animal, second_user_profile, logged_in_client):
        from ahc.apps.animals.models import AnimalShare

        carer_user, carer_profile = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer_profile, allow_history=False, allow_biometrics=True)
        c = logged_in_client(carer_user)
        assert c.get(f"/pet/{animal.id}/tab/biometrics/", HTTP_HX_REQUEST="true").status_code == 200
        assert c.get(f"/pet/{animal.id}/tab/notes/", HTTP_HX_REQUEST="true").status_code == 403


def _create_biometric_weight(
    animal, profile, weight, unit="kg", date_event_started=None, backdate_creation=None, description="Weigh-in"
):
    from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
    from ahc.apps.medical_notes.services.biometrics import create_biometric_record

    note = MedicalRecord.objects.create(
        animal=animal,
        author=profile,
        short_description=description,
        type_of_event="biometric_record",
        date_event_started=date_event_started,
    )
    if backdate_creation is not None:
        MedicalRecord.objects.filter(pk=note.pk).update(date_creation=backdate_creation)
        note.refresh_from_db()
    return create_biometric_record(animal, note, "weight", {"weight": weight, "weight_unit_to_present": unit})


def _create_biometric_height(
    animal, profile, height, unit="cm", date_event_started=None, backdate_creation=None, description="Height check"
):
    from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
    from ahc.apps.medical_notes.services.biometrics import create_biometric_record

    note = MedicalRecord.objects.create(
        animal=animal,
        author=profile,
        short_description=description,
        type_of_event="biometric_record",
        date_event_started=date_event_started,
    )
    if backdate_creation is not None:
        MedicalRecord.objects.filter(pk=note.pk).update(date_creation=backdate_creation)
        note.refresh_from_db()
    return create_biometric_record(animal, note, "height", {"height": height, "height_unit_to_present": unit})


@pytest.mark.integration
@pytest.mark.django_db
class TestBiometricsTabData:
    """_build_biometrics / _resolve_biometric_date: date cascade, unit grouping, sorting, custom handling."""

    @pytest.fixture
    def animal(self, db, user_profile):
        _, profile = user_profile
        return Animal.objects.create(full_name="Luna", owner=profile)

    def _get(self, client, animal):
        return client.get(f"/pet/{animal.id}/tab/biometrics/", HTTP_HX_REQUEST="true")

    def test_date_event_started_wins(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        _create_biometric_weight(animal, profile, 4.2, date_event_started=date(2026, 1, 1))
        response = self._get(logged_in_client(user), animal)
        assert response.context["history_rows"][0]["date"] == date(2026, 1, 1)

    def test_fallback_to_localized_date_creation(self, animal, user_profile, logged_in_client):
        """No date_event_started: falls back to date_creation, localized to Europe/Warsaw.

        2026-01-10 23:30 UTC is 2026-01-11 00:30 in Warsaw (UTC+1, no DST in January) —
        a bare `.date()` on the stored UTC value (skipping localtime()) would wrongly
        resolve to 2026-01-10.
        """
        from datetime import UTC
        from datetime import datetime as dt

        user, profile = user_profile
        utc_instant = dt(2026, 1, 10, 23, 30, tzinfo=UTC)
        _create_biometric_weight(animal, profile, 4.2, backdate_creation=utc_instant)
        response = self._get(logged_in_client(user), animal)
        assert response.context["history_rows"][0]["date"] == date(2026, 1, 11)

    def test_fallback_to_date_updated_when_related_note_is_none(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        record = _create_biometric_weight(animal, profile, 4.2)
        expected = timezone.localtime(record.date_updated).date()
        # Simulate the note having been deleted (SET_NULL) without re-triggering signals.
        from ahc.apps.medical_notes.models.type_measurement_notes import BiometricRecord

        BiometricRecord.objects.filter(pk=record.pk).update(related_note=None)

        response = self._get(logged_in_client(user), animal)
        assert response.context["history_rows"][0]["date"] == expected
        assert response.context["history_rows"][0]["context"] == ""

    def test_weight_grouped_by_unit(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        _create_biometric_weight(animal, profile, 4.2, unit="kg", date_event_started=date(2026, 1, 1))
        _create_biometric_weight(animal, profile, 4200, unit="g", date_event_started=date(2026, 1, 2))

        response = self._get(logged_in_client(user), animal)
        series = response.context["chart_series"]
        assert {s["unit"] for s in series} == {"kg", "g"}
        assert {s["label"] for s in series} == {"Weight (kg)", "Weight (g)"}

    def test_chart_points_ascending_history_rows_descending(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        _create_biometric_weight(animal, profile, 4.0, date_event_started=date(2026, 1, 10))
        _create_biometric_weight(animal, profile, 4.1, date_event_started=date(2026, 1, 1))
        _create_biometric_weight(animal, profile, 4.2, date_event_started=date(2026, 1, 20))

        response = self._get(logged_in_client(user), animal)
        points = response.context["chart_series"][0]["points"]
        assert [p["date"] for p in points] == ["2026-01-01", "2026-01-10", "2026-01-20"]

        rows = response.context["history_rows"]
        assert [r["date"] for r in rows] == [date(2026, 1, 20), date(2026, 1, 10), date(2026, 1, 1)]

    def test_history_rows_tie_break_by_id_descending(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        first = _create_biometric_weight(animal, profile, 4.0, date_event_started=date(2026, 1, 1))
        second = _create_biometric_weight(animal, profile, 4.1, date_event_started=date(2026, 1, 1))

        response = self._get(logged_in_client(user), animal)
        rows = response.context["history_rows"]
        assert [r["id"] for r in rows] == [second.id, first.id]

    def test_custom_visible_in_history_but_not_charted(self, animal, user_profile, logged_in_client):
        from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
        from ahc.apps.medical_notes.services.biometrics import create_biometric_record

        user, profile = user_profile
        _create_biometric_weight(animal, profile, 4.0, date_event_started=date(2026, 1, 1))
        note = MedicalRecord.objects.create(
            animal=animal,
            author=profile,
            short_description="Fur check",
            type_of_event="biometric_record",
            date_event_started=date(2026, 1, 2),
        )
        create_biometric_record(
            animal, note, "custom", {"custom_name": "Fur density", "custom_value": "soft", "custom_unit": ""}
        )

        response = self._get(logged_in_client(user), animal)
        types = {r["measurement_type"] for r in response.context["history_rows"]}
        assert types == {"weight", "custom"}
        assert all(s["measurement_type"] == "weight" for s in response.context["chart_series"])
        custom_row = next(r for r in response.context["history_rows"] if r["measurement_type"] == "custom")
        assert custom_row["value"] == "soft"

    def test_height_produces_chart_series(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        _create_biometric_height(animal, profile, 31.0, date_event_started=date(2026, 1, 1))

        response = self._get(logged_in_client(user), animal)
        series = response.context["chart_series"]
        assert len(series) == 1
        assert series[0]["measurement_type"] == "height"
        assert series[0]["label"] == "Height (cm)"

    def test_height_grouped_by_unit(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        _create_biometric_height(animal, profile, 31.0, unit="cm", date_event_started=date(2026, 1, 1))
        _create_biometric_height(animal, profile, 320, unit="mm", date_event_started=date(2026, 1, 2))

        response = self._get(logged_in_client(user), animal)
        series = response.context["chart_series"]
        assert {s["unit"] for s in series} == {"cm", "mm"}
        assert {s["label"] for s in series} == {"Height (cm)", "Height (mm)"}

    def test_weight_and_height_together_both_charted(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        _create_biometric_weight(animal, profile, 4.2, unit="kg", date_event_started=date(2026, 1, 1))
        _create_biometric_height(animal, profile, 31.0, unit="cm", date_event_started=date(2026, 1, 2))

        response = self._get(logged_in_client(user), animal)
        series = response.context["chart_series"]
        assert {s["measurement_type"] for s in series} == {"weight", "height"}

        types = {r["measurement_type"] for r in response.context["history_rows"]}
        assert types == {"weight", "height"}

    def test_chart_series_ordering_weight_before_height_units_alphabetical(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        # Created in scrambled order to prove ordering does not depend on insertion order.
        _create_biometric_height(animal, profile, 320, unit="mm", date_event_started=date(2026, 1, 1))
        _create_biometric_weight(animal, profile, 4.2, unit="kg", date_event_started=date(2026, 1, 2))
        _create_biometric_height(animal, profile, 31.0, unit="cm", date_event_started=date(2026, 1, 3))
        _create_biometric_weight(animal, profile, 4200, unit="g", date_event_started=date(2026, 1, 4))

        response = self._get(logged_in_client(user), animal)
        series = response.context["chart_series"]
        assert [s["label"] for s in series] == ["Weight (g)", "Weight (kg)", "Height (cm)", "Height (mm)"]

    def test_height_chart_points_ascending_by_resolved_date(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        _create_biometric_height(animal, profile, 32.0, date_event_started=date(2026, 1, 20))
        _create_biometric_height(animal, profile, 31.0, date_event_started=date(2026, 1, 1))
        _create_biometric_height(animal, profile, 31.5, date_event_started=date(2026, 1, 10))

        response = self._get(logged_in_client(user), animal)
        points = response.context["chart_series"][0]["points"]
        assert [p["date"] for p in points] == ["2026-01-01", "2026-01-10", "2026-01-20"]

    def test_only_custom_no_chart_canvas(self, animal, user_profile, logged_in_client):
        from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
        from ahc.apps.medical_notes.services.biometrics import create_biometric_record

        user, profile = user_profile
        note = MedicalRecord.objects.create(
            animal=animal,
            author=profile,
            short_description="Fur check",
            type_of_event="biometric_record",
            date_event_started=date(2026, 1, 1),
        )
        create_biometric_record(
            animal, note, "custom", {"custom_name": "Fur density", "custom_value": "soft", "custom_unit": ""}
        )

        response = self._get(logged_in_client(user), animal)
        assert response.context["chart_series"] == []
        content = response.content.decode()
        assert "biometric-chart-data" not in content
        assert "data-biometric-chart" not in content

    def test_only_height_renders_canvas(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        _create_biometric_height(animal, profile, 31.0, date_event_started=date(2026, 1, 1))

        response = self._get(logged_in_client(user), animal)
        content = response.content.decode()
        assert content.count("data-biometric-chart") == 1
        assert "Height (cm)" in content

    def test_single_height_point_chart_payload(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        _create_biometric_height(animal, profile, 31.0, date_event_started=date(2026, 1, 1))

        response = self._get(logged_in_client(user), animal)
        points = response.context["chart_series"][0]["points"]
        assert len(points) == 1
        assert points[0] == {"date": "2026-01-01", "value": 31.0}

    def test_record_without_any_subtype_is_skipped_not_crashed(self, animal, user_profile, logged_in_client):
        from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
        from ahc.apps.medical_notes.models.type_measurement_notes import BiometricRecord

        user, profile = user_profile
        note = MedicalRecord.objects.create(
            animal=animal, author=profile, short_description="Corrupted", type_of_event="biometric_record"
        )
        BiometricRecord.objects.create(animal=animal, related_note=note)

        response = self._get(logged_in_client(user), animal)
        assert response.status_code == 200
        assert response.context["history_rows"] == []

    def test_selector_has_no_n_plus_1(self, animal, user_profile, logged_in_client):
        """Query count must stay flat regardless of how many records or measurement types exist."""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        from ahc.apps.medical_notes.models.type_basic_note import MedicalRecord
        from ahc.apps.medical_notes.services.biometrics import create_biometric_record

        user, profile = user_profile
        client = logged_in_client(user)

        _create_biometric_weight(animal, profile, 4.0, date_event_started=date(2026, 1, 1))
        with CaptureQueriesContext(connection) as ctx_one:
            self._get(client, animal)

        _create_biometric_weight(animal, profile, 4.1, date_event_started=date(2026, 1, 2))
        _create_biometric_height(animal, profile, 31.0, date_event_started=date(2026, 1, 3))
        _create_biometric_height(animal, profile, 31.5, unit="mm", date_event_started=date(2026, 1, 4))
        note = MedicalRecord.objects.create(
            animal=animal,
            author=profile,
            short_description="Fur check",
            type_of_event="biometric_record",
            date_event_started=date(2026, 1, 5),
        )
        create_biometric_record(
            animal, note, "custom", {"custom_name": "Fur density", "custom_value": "soft", "custom_unit": ""}
        )
        with CaptureQueriesContext(connection) as ctx_five:
            self._get(client, animal)

        assert len(ctx_five.captured_queries) == len(ctx_one.captured_queries)

    def test_empty_state_no_canvas_no_data_script(self, animal, user_profile, logged_in_client):
        user, _ = user_profile
        response = self._get(logged_in_client(user), animal)
        content = response.content.decode()
        assert "No biometric records yet." in content
        assert "biometric-chart-data" not in content

    def test_single_point_still_renders_chart_card(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        _create_biometric_weight(animal, profile, 4.2, date_event_started=date(2026, 1, 1))
        response = self._get(logged_in_client(user), animal)
        content = response.content.decode()
        assert 'id="biometric-chart-data"' in content
        assert content.count("data-biometric-chart") == 1

    def test_multiple_weight_units_render_separate_cards(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        _create_biometric_weight(animal, profile, 4.2, unit="kg", date_event_started=date(2026, 1, 1))
        _create_biometric_weight(animal, profile, 4200, unit="g", date_event_started=date(2026, 1, 2))
        response = self._get(logged_in_client(user), animal)
        content = response.content.decode()
        assert content.count("data-biometric-chart") == 2
        assert "Weight (kg)" in content
        assert "Weight (g)" in content

    def test_history_table_shows_value_and_unit(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        _create_biometric_weight(animal, profile, 4.2, unit="kg", date_event_started=date(2026, 1, 1))
        response = self._get(logged_in_client(user), animal)
        content = response.content.decode()
        assert "4.2" in content
        assert "kg" in content

    def test_htmx_response_is_fragment_direct_navigation_is_full_shell(self, animal, user_profile, logged_in_client):
        user, _ = user_profile
        c = logged_in_client(user)
        fragment = c.get(f"/pet/{animal.id}/tab/biometrics/", HTTP_HX_REQUEST="true")
        full = c.get(f"/pet/{animal.id}/tab/biometrics/")
        assert "<title>" not in fragment.content.decode()
        assert "<title>" in full.content.decode()
