import importlib

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from ahc.apps.veterinary.models import MedicalPlace as RealMedicalPlace
from ahc.apps.veterinary.models import Vet as RealVet

_migration = importlib.import_module("ahc.apps.animals.migrations.0009_migrate_first_contact_text")
_split_legacy_text = _migration._split_legacy_text

MIGRATE_FROM = [("animals", "0008_add_first_contact_record_fks")]
MIGRATE_TO = [("animals", "0009_migrate_first_contact_text")]


def _restore_to_latest():
    """Bring every app back to its leaf migration so later tests see the normal schema."""
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.unit
def test_single_line_gives_name_and_empty_details():
    assert _split_legacy_text("Dr Kowalski") == ("Dr Kowalski", "")


@pytest.mark.unit
def test_multiple_lines_split_first_line_as_name():
    assert _split_legacy_text("Dr Kowalski\ntel. 123\nul. Testowa") == ("Dr Kowalski", "tel. 123\nul. Testowa")


@pytest.mark.unit
def test_crlf_is_normalized_to_lf():
    assert _split_legacy_text("Dr Kowalski\r\ntel. 123") == ("Dr Kowalski", "tel. 123")


@pytest.mark.unit
def test_blank_line_right_after_first_line_is_preserved():
    """Guards the round-trip invariant: name + '\\n' + details == normalized legacy text."""
    name, details = _split_legacy_text("Dr Kowalski\n\ntylko nagłe przypadki")
    assert name == "Dr Kowalski"
    assert details == "\ntylko nagłe przypadki"
    assert name + "\n" + details == "Dr Kowalski\n\ntylko nagłe przypadki"


@pytest.mark.unit
def test_250_char_first_line_stays_whole():
    long_name = "A" * 250
    assert _split_legacy_text(long_name) == (long_name, "")


@pytest.mark.unit
@pytest.mark.parametrize("text", ["", "   ", "\n\n  \n", None])
def test_blank_or_none_text_returns_none(text):
    assert _split_legacy_text(text) is None


@pytest.mark.integration
@pytest.mark.django_db(transaction=True)
def test_forward_migration_materializes_and_dedupes_contacts(user_profile, second_user_profile):
    """Runs the real 0008 -> 0009 migration and covers scenarios A, B, C, D, E, F, G, H, I."""
    _, owner_a = user_profile
    _, owner_b = second_user_profile

    executor = MigrationExecutor(connection)
    executor.migrate(MIGRATE_FROM)
    old_apps = executor.loader.project_state(MIGRATE_FROM).apps
    HistoricalAnimal = old_apps.get_model("animals", "Animal")
    HistoricalVet = old_apps.get_model("veterinary", "Vet")
    HistoricalMedicalPlace = old_apps.get_model("veterinary", "MedicalPlace")

    try:
        # A: basic vet materialization, and reused as the dedup target for D.
        vet_text = "Dr Kowalski\ntel. 123"
        animal_a1 = HistoricalAnimal.objects.create(full_name="Rex", owner_id=owner_a.pk, legacy_first_contact_vet=vet_text)
        animal_a2 = HistoricalAnimal.objects.create(
            full_name="Fido", owner_id=owner_a.pk, legacy_first_contact_vet=vet_text
        )

        # B: an empty line right after the name must round-trip through as_contact_text().
        blank_line_text = "Dr Kowalski\n\ntylko nagłe przypadki"
        animal_blank = HistoricalAnimal.objects.create(
            full_name="Luna", owner_id=owner_a.pk, legacy_first_contact_vet=blank_line_text
        )

        # C: MedicalPlace materialization.
        place_text = "Happy Paws Clinic\nul. Testowa 1"
        animal_place = HistoricalAnimal.objects.create(
            full_name="Burek", owner_id=owner_a.pk, legacy_first_contact_medical_place=place_text
        )

        # E: same first line, different remaining details -> two distinct Vet records.
        vet_text_other_details = "Dr Kowalski\ntel. 222"
        animal_e = HistoricalAnimal.objects.create(
            full_name="Cat", owner_id=owner_a.pk, legacy_first_contact_vet=vet_text_other_details
        )

        # F: identical text, different owner -> owner-scoped, separate record.
        animal_f = HistoricalAnimal.objects.create(
            full_name="Reksio", owner_id=owner_b.pk, legacy_first_contact_vet=vet_text
        )

        # G: a pre-existing, exactly matching Vet must be reused instead of duplicated.
        pre_existing_vet = HistoricalVet.objects.create(
            owner_id=owner_a.pk, name="Existing Vet", phone="", email="", details="tel. 999"
        )
        animal_g = HistoricalAnimal.objects.create(
            full_name="Azor", owner_id=owner_a.pk, legacy_first_contact_vet="Existing Vet\ntel. 999"
        )

        # H: an already-set FK must not be replaced, even though legacy text still exists.
        already_linked_vet = HistoricalVet.objects.create(
            owner_id=owner_a.pk, name="Already Linked", phone="", email="", details=""
        )
        animal_h = HistoricalAnimal.objects.create(
            full_name="Bella",
            owner_id=owner_a.pk,
            legacy_first_contact_vet="Some other text\nthat should be ignored",
            first_contact_vet_id=already_linked_vet.pk,
        )

        # I: an ownerless animal must be skipped entirely; no orphan contact may be created.
        animal_i = HistoricalAnimal.objects.create(
            full_name="Stray", owner_id=None, legacy_first_contact_vet="Dr Nikt\ntel. 000"
        )

        vet_count_before = HistoricalVet.objects.count()
        place_count_before = HistoricalMedicalPlace.objects.count()

        executor.loader.build_graph()
        executor.migrate(MIGRATE_TO)

        new_apps = executor.loader.project_state(MIGRATE_TO).apps
        Animal = new_apps.get_model("animals", "Animal")

        def refresh(animal):
            return Animal.objects.get(pk=animal.pk)

        a1 = refresh(animal_a1)
        vet_a1 = RealVet.objects.get(pk=a1.first_contact_vet_id)
        assert vet_a1.owner.pk == owner_a.pk
        assert vet_a1.name == "Dr Kowalski"
        assert vet_a1.details == "tel. 123"
        assert a1.legacy_first_contact_vet == vet_text

        # D: dedup within the same forward pass.
        a2 = refresh(animal_a2)
        assert a2.first_contact_vet_id == a1.first_contact_vet_id
        assert RealVet.objects.filter(owner_id=owner_a.pk, name="Dr Kowalski", details="tel. 123").count() == 1

        blank = refresh(animal_blank)
        vet_blank = RealVet.objects.get(pk=blank.first_contact_vet_id)
        assert vet_blank.name == "Dr Kowalski"
        assert vet_blank.details == "\ntylko nagłe przypadki"
        assert vet_blank.as_contact_text() == blank.legacy_first_contact_vet

        place_animal = refresh(animal_place)
        place = RealMedicalPlace.objects.get(pk=place_animal.first_contact_medical_place_id)
        assert place.owner.pk == owner_a.pk
        assert place.name == "Happy Paws Clinic"
        assert place.details == "ul. Testowa 1"
        assert place.as_contact_text() == place_animal.legacy_first_contact_medical_place

        e = refresh(animal_e)
        vet_e = RealVet.objects.get(pk=e.first_contact_vet_id)
        assert vet_e.pk != vet_a1.pk
        assert vet_e.name == vet_a1.name == "Dr Kowalski"
        assert vet_e.details == "tel. 222"

        f = refresh(animal_f)
        vet_f = RealVet.objects.get(pk=f.first_contact_vet_id)
        assert vet_f.pk != vet_a1.pk
        assert vet_f.owner.pk == owner_b.pk
        assert vet_f.name == "Dr Kowalski"
        assert vet_f.details == "tel. 123"

        g = refresh(animal_g)
        assert g.first_contact_vet_id == pre_existing_vet.pk
        assert RealVet.objects.filter(owner_id=owner_a.pk, name="Existing Vet").count() == 1

        h = refresh(animal_h)
        assert h.first_contact_vet_id == already_linked_vet.pk
        assert h.legacy_first_contact_vet == "Some other text\nthat should be ignored"

        i = refresh(animal_i)
        assert i.first_contact_vet_id is None
        assert i.legacy_first_contact_vet == "Dr Nikt\ntel. 000"

        # g and h reused existing rows, i was skipped: only 4 new Vets and 1 new MedicalPlace.
        assert HistoricalVet.objects.count() - vet_count_before == 4
        assert HistoricalMedicalPlace.objects.count() - place_count_before == 1
    finally:
        _restore_to_latest()


@pytest.mark.integration
@pytest.mark.django_db(transaction=True)
def test_forward_migration_is_idempotent_across_a_revert_cycle(user_profile):
    """J: 0008 -> 0009 -> 0008 -> 0009 must not create a duplicate contact or move the FK."""
    _, owner = user_profile

    executor = MigrationExecutor(connection)
    executor.migrate(MIGRATE_FROM)
    old_apps = executor.loader.project_state(MIGRATE_FROM).apps
    HistoricalAnimal = old_apps.get_model("animals", "Animal")
    HistoricalVet = old_apps.get_model("veterinary", "Vet")

    try:
        text = "Dr Idempotent\ntel. 555"
        animal = HistoricalAnimal.objects.create(full_name="Reksio2", owner_id=owner.pk, legacy_first_contact_vet=text)

        executor.loader.build_graph()
        executor.migrate(MIGRATE_TO)

        new_apps = executor.loader.project_state(MIGRATE_TO).apps
        Animal = new_apps.get_model("animals", "Animal")
        first_pass_animal = Animal.objects.get(pk=animal.pk)
        first_vet_id = first_pass_animal.first_contact_vet_id
        assert first_vet_id is not None
        assert HistoricalVet.objects.filter(owner_id=owner.pk, name="Dr Idempotent").count() == 1

        # Revert (noop) to 0008 and forward again: the Vet row and FK survive since noop touches no data.
        executor.migrate(MIGRATE_FROM)
        executor.loader.build_graph()
        executor.migrate(MIGRATE_TO)

        new_apps = executor.loader.project_state(MIGRATE_TO).apps
        Animal = new_apps.get_model("animals", "Animal")
        second_pass_animal = Animal.objects.get(pk=animal.pk)

        assert second_pass_animal.first_contact_vet_id == first_vet_id
        assert HistoricalVet.objects.filter(owner_id=owner.pk, name="Dr Idempotent").count() == 1
        assert second_pass_animal.legacy_first_contact_vet == text
    finally:
        _restore_to_latest()
