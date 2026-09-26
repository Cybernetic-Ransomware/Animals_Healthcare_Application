from datetime import date

import pytest

from ahc.apps.animals.models import Animal, AnimalShare
from ahc.apps.veterinary.models import MedicalPlace, Vet


@pytest.mark.integration
@pytest.mark.django_db
class TestRemoveKeeperView:
    """RemoveKeeperView: owner POST removes keeper; non-owner gets 403."""

    @pytest.fixture
    def animal_with_keeper(self, db, user_profile, second_user_profile):
        _, owner_profile = user_profile
        _, keeper_profile = second_user_profile
        a = Animal.objects.create(full_name="Rex", owner=owner_profile)
        a.allowed_users.add(keeper_profile)
        return a

    def test_owner_post_removes_keeper_and_redirects(
        self, animal_with_keeper, user_profile, second_user_profile, logged_in_client
    ):
        owner_user, _ = user_profile
        _, keeper_profile = second_user_profile
        url = f"/pet/{animal_with_keeper.id}/keepers/{keeper_profile.pk}/remove/"
        response = logged_in_client(owner_user).post(url)
        assert response.status_code == 302
        animal_with_keeper.refresh_from_db()
        assert not animal_with_keeper.allowed_users.filter(pk=keeper_profile.pk).exists()

    def test_non_owner_post_returns_403(self, animal_with_keeper, second_user_profile, logged_in_client):
        keeper_user, keeper_profile = second_user_profile
        url = f"/pet/{animal_with_keeper.id}/keepers/{keeper_profile.pk}/remove/"
        response = logged_in_client(keeper_user).post(url)
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.django_db
class TestAnimalDeleteView:
    """AnimalDeleteView: confirmation page and owner-only delete."""

    @pytest.fixture
    def animal(self, db, user_profile):
        _, profile = user_profile
        return Animal.objects.create(full_name="ToDelete", owner=profile)

    def test_owner_get_returns_200(self, animal, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).get(f"/pet/{animal.id}/delete/")
        assert response.status_code == 200

    def test_owner_post_deletes_animal_and_redirects(self, animal, user_profile, logged_in_client):
        user, _ = user_profile
        pk = animal.id
        response = logged_in_client(user).post(f"/pet/{pk}/delete/")
        assert response.status_code == 302
        assert not Animal.objects.filter(pk=pk).exists()

    def test_non_owner_post_returns_403(self, animal, second_user_profile, logged_in_client):
        other_user, _ = second_user_profile
        response = logged_in_client(other_user).post(f"/pet/{animal.id}/delete/")
        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.django_db
class TestImageUploadView:
    """ImageUploadView: profile_image is required on this dedicated upload screen."""

    @pytest.fixture
    def animal(self, db, user_profile):
        _, profile = user_profile
        return Animal.objects.create(full_name="UploadTarget", owner=profile)

    @pytest.fixture(autouse=True)
    def _media_root(self, tmp_path, settings):
        settings.MEDIA_ROOT = tmp_path
        (tmp_path / "profile_pics" / "animals").mkdir(parents=True)

    def test_post_without_file_is_invalid_and_does_not_crash(self, animal, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).post(f"/pet/{animal.id}/upload-image/", {})
        assert response.status_code == 200
        assert response.context["form"].errors["profile_image"]
        animal.refresh_from_db()
        assert animal.profile_image.name == ""

    def test_valid_post_saves_image_and_redirects(self, animal, user_profile, logged_in_client, png_upload):
        user, _ = user_profile
        response = logged_in_client(user).post(f"/pet/{animal.id}/upload-image/", {"profile_image": png_upload()})
        assert response.status_code == 302
        animal.refresh_from_db()
        assert animal.profile_image.name != ""


@pytest.mark.integration
@pytest.mark.django_db
class TestChangeBirthdayView:
    """ChangeBirthdayView: birthdate update behind owner-only gate."""

    @pytest.fixture
    def animal(self, db, user_profile):
        _, profile = user_profile
        return Animal.objects.create(full_name="BdayAnimal", owner=profile)

    def test_owner_get_returns_200(self, animal, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).get(f"/pet/{animal.id}/btd/")
        assert response.status_code == 200

    def test_non_owner_get_returns_403(self, animal, second_user_profile, logged_in_client):
        other_user, _ = second_user_profile
        response = logged_in_client(other_user).get(f"/pet/{animal.id}/btd/")
        assert response.status_code == 403

    def test_valid_post_saves_birthdate_and_redirects(self, animal, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).post(f"/pet/{animal.id}/btd/", {"birthdate": "2020-03-15"})
        assert response.status_code == 302
        animal.refresh_from_db()
        assert animal.birthdate == date(2020, 3, 15)


@pytest.mark.integration
@pytest.mark.django_db
class TestChangeFirstContactView:
    """ChangeFirstContactView: pick first-contact Vet/MedicalPlace from the owner's contact book."""

    @pytest.fixture
    def animal(self, db, user_profile):
        _, profile = user_profile
        return Animal.objects.create(full_name="FirstContactAnimal", owner=profile)

    def test_owner_get_returns_200(self, animal, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).get(f"/pet/{animal.id}/cnt/")
        assert response.status_code == 200

    def test_non_owner_get_returns_403(self, animal, second_user_profile, logged_in_client):
        other_user, _ = second_user_profile
        response = logged_in_client(other_user).get(f"/pet/{animal.id}/cnt/")
        assert response.status_code == 403

    def test_carer_get_returns_403(self, animal, second_user_profile, logged_in_client):
        carer_user, carer_profile = second_user_profile
        AnimalShare.objects.create(animal=animal, carer=carer_profile, allow_vet_contact=True)
        response = logged_in_client(carer_user).get(f"/pet/{animal.id}/cnt/")
        assert response.status_code == 403

    def test_valid_post_saves_vet_and_place(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        vet = Vet.objects.create(name="Dr Kowalski", owner=profile)
        place = MedicalPlace.objects.create(name="City Vet Clinic", owner=profile)

        response = logged_in_client(user).post(
            f"/pet/{animal.id}/cnt/",
            {"first_contact_vet": vet.pk, "first_contact_medical_place": place.pk},
        )

        assert response.status_code == 302
        animal.refresh_from_db()
        assert animal.first_contact_vet == vet
        assert animal.first_contact_medical_place == place

    def test_post_with_empty_values_clears_both_fk(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        vet = Vet.objects.create(name="Dr Kowalski", owner=profile)
        place = MedicalPlace.objects.create(name="City Vet Clinic", owner=profile)
        animal.first_contact_vet = vet
        animal.first_contact_medical_place = place
        animal.save()

        response = logged_in_client(user).post(
            f"/pet/{animal.id}/cnt/", {"first_contact_vet": "", "first_contact_medical_place": ""}
        )

        assert response.status_code == 302
        animal.refresh_from_db()
        assert animal.first_contact_vet is None
        assert animal.first_contact_medical_place is None

    def test_post_with_another_owners_vet_is_invalid_and_saves_nothing(
        self, animal, user_profile, second_user_profile, logged_in_client
    ):
        user, _ = user_profile
        _, other_profile = second_user_profile
        other_vet = Vet.objects.create(name="Dr Nowak", owner=other_profile)

        response = logged_in_client(user).post(f"/pet/{animal.id}/cnt/", {"first_contact_vet": other_vet.pk})

        assert response.status_code == 200
        assert not response.context["form"].is_valid()
        animal.refresh_from_db()
        assert animal.first_contact_vet is None

    def test_post_with_another_owners_medical_place_is_invalid_and_saves_nothing(
        self, animal, user_profile, second_user_profile, logged_in_client
    ):
        user, _ = user_profile
        _, other_profile = second_user_profile
        other_place = MedicalPlace.objects.create(name="Other Clinic", owner=other_profile)

        response = logged_in_client(user).post(f"/pet/{animal.id}/cnt/", {"first_contact_medical_place": other_place.pk})

        assert response.status_code == 200
        assert not response.context["form"].is_valid()
        animal.refresh_from_db()
        assert animal.first_contact_medical_place is None

    def test_get_shows_current_fk_as_initial_values(self, animal, user_profile, logged_in_client):
        user, profile = user_profile
        vet = Vet.objects.create(name="Dr Kowalski", owner=profile)
        place = MedicalPlace.objects.create(name="City Vet Clinic", owner=profile)
        animal.first_contact_vet = vet
        animal.first_contact_medical_place = place
        animal.save()

        response = logged_in_client(user).get(f"/pet/{animal.id}/cnt/")

        form = response.context["form"]
        assert form.initial["first_contact_vet"] == vet
        assert form.initial["first_contact_medical_place"] == place

    def test_vet_queryset_only_contains_the_animals_owners_contacts(
        self, animal, user_profile, second_user_profile, logged_in_client
    ):
        user, profile = user_profile
        _, other_profile = second_user_profile
        own_vet = Vet.objects.create(name="Dr Kowalski", owner=profile)
        Vet.objects.create(name="Dr Nowak", owner=other_profile)

        response = logged_in_client(user).get(f"/pet/{animal.id}/cnt/")

        queryset = response.context["form"].fields["first_contact_vet"].queryset
        assert list(queryset) == [own_vet]

    def test_medical_place_queryset_only_contains_the_animals_owners_contacts(
        self, animal, user_profile, second_user_profile, logged_in_client
    ):
        user, profile = user_profile
        _, other_profile = second_user_profile
        own_place = MedicalPlace.objects.create(name="City Vet Clinic", owner=profile)
        MedicalPlace.objects.create(name="Other Clinic", owner=other_profile)

        response = logged_in_client(user).get(f"/pet/{animal.id}/cnt/")

        queryset = response.context["form"].fields["first_contact_medical_place"].queryset
        assert list(queryset) == [own_place]

    @pytest.mark.regression
    def test_owner_get_on_deceased_animal_returns_403(self, user_profile, logged_in_client):
        """Guards the deceased-write gap from the plan's §1 analysis, characterized in PR #66."""
        user, profile = user_profile
        animal = Animal.objects.create(full_name="Passed", owner=profile, date_of_death=date(2024, 3, 15))

        response = logged_in_client(user).get(f"/pet/{animal.id}/cnt/")

        assert response.status_code == 403

    @pytest.mark.regression
    def test_owner_post_on_deceased_animal_returns_403_and_does_not_change_fk(self, user_profile, logged_in_client):
        """Guards the deceased-write gap from the plan's §1 analysis, characterized in PR #66."""
        user, profile = user_profile
        vet = Vet.objects.create(name="Dr Kowalski", owner=profile)
        animal = Animal.objects.create(full_name="Passed", owner=profile, date_of_death=date(2024, 3, 15))

        response = logged_in_client(user).post(f"/pet/{animal.id}/cnt/", {"first_contact_vet": vet.pk})

        assert response.status_code == 403
        animal.refresh_from_db()
        assert animal.first_contact_vet is None


@pytest.mark.integration
@pytest.mark.django_db
class TestChangeNextVisitView:
    """ChangeNextVisitView: next_visit_date update with vet-tab redirect."""

    @pytest.fixture
    def animal(self, db, user_profile):
        _, profile = user_profile
        return Animal.objects.create(full_name="NextVisitAnimal", owner=profile)

    def test_owner_get_returns_200(self, animal, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).get(f"/pet/{animal.id}/next-visit/")
        assert response.status_code == 200

    def test_non_owner_get_returns_403(self, animal, second_user_profile, logged_in_client):
        other_user, _ = second_user_profile
        response = logged_in_client(other_user).get(f"/pet/{animal.id}/next-visit/")
        assert response.status_code == 403

    def test_valid_post_saves_date_and_redirects_to_vet_tab(self, animal, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).post(f"/pet/{animal.id}/next-visit/", {"next_visit_date": "2026-09-01"})
        assert response.status_code == 302
        animal.refresh_from_db()
        assert animal.next_visit_date == date(2026, 9, 1)
        assert f"/pet/{animal.id}/tab/vet/" in response["Location"]


@pytest.mark.integration
@pytest.mark.django_db
class TestChangeDietaryRestrictionsView:
    """ChangeDietaryRestrictionsView: dietary_restrictions update with diet-tab redirect."""

    @pytest.fixture
    def animal(self, db, user_profile):
        _, profile = user_profile
        return Animal.objects.create(full_name="DietAnimal", owner=profile)

    def test_owner_get_returns_200(self, animal, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).get(f"/pet/{animal.id}/dietary-restrictions/")
        assert response.status_code == 200

    def test_non_owner_get_returns_403(self, animal, second_user_profile, logged_in_client):
        other_user, _ = second_user_profile
        response = logged_in_client(other_user).get(f"/pet/{animal.id}/dietary-restrictions/")
        assert response.status_code == 403

    def test_valid_post_saves_restrictions_and_redirects_to_diet_tab(self, animal, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).post(
            f"/pet/{animal.id}/dietary-restrictions/", {"dietary_restrictions": "No grapes, no onions"}
        )
        assert response.status_code == 302
        animal.refresh_from_db()
        assert animal.dietary_restrictions == "No grapes, no onions"
        assert f"/pet/{animal.id}/tab/diet/" in response["Location"]


@pytest.mark.integration
@pytest.mark.django_db
class TestChangeAnimalDetailsView:
    """ChangeAnimalDetailsView: species/breed/sex/sterilization update with settings-tab redirect."""

    @pytest.fixture
    def animal(self, db, user_profile):
        _, profile = user_profile
        return Animal.objects.create(full_name="DetailsAnimal", owner=profile)

    def test_owner_get_returns_200(self, animal, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).get(f"/pet/{animal.id}/details/")
        assert response.status_code == 200

    def test_non_owner_get_returns_403(self, animal, second_user_profile, logged_in_client):
        other_user, _ = second_user_profile
        response = logged_in_client(other_user).get(f"/pet/{animal.id}/details/")
        assert response.status_code == 403

    def test_valid_post_saves_details_and_redirects_to_settings_tab(self, animal, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).post(
            f"/pet/{animal.id}/details/",
            {"species": "cat", "breed": "Maine Coon", "sex": "f", "sterilization": "on"},
        )
        assert response.status_code == 302
        animal.refresh_from_db()
        assert animal.species == "cat"
        assert animal.breed == "Maine Coon"
        assert animal.sex == "f"
        assert animal.sterilization is True
        assert f"/pet/{animal.id}/tab/settings/" in response["Location"]


@pytest.mark.integration
@pytest.mark.django_db
class TestManageKeepersView:
    """ManageKeepersView: share creation behind owner-only gate."""

    @pytest.fixture
    def animal(self, db, user_profile):
        _, profile = user_profile
        return Animal.objects.create(full_name="KeeperAnimal", owner=profile)

    def test_owner_get_returns_200(self, animal, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).get(f"/pet/{animal.id}/manage_keepers/")
        assert response.status_code == 200

    def test_non_owner_get_returns_403(self, animal, second_user_profile, logged_in_client):
        other_user, _ = second_user_profile
        response = logged_in_client(other_user).get(f"/pet/{animal.id}/manage_keepers/")
        assert response.status_code == 403

    def test_valid_post_creates_share_for_new_keeper(self, animal, user_profile, second_user_profile, logged_in_client):
        user, _ = user_profile
        _, keeper_profile = second_user_profile
        response = logged_in_client(user).post(
            f"/pet/{animal.id}/manage_keepers/",
            {"input_user": keeper_profile.user.username, "allow_basic": "on"},
        )
        assert response.status_code == 302
        assert AnimalShare.objects.filter(animal=animal, carer=keeper_profile).exists()


@pytest.mark.integration
@pytest.mark.django_db
class TestChangeOwnerView:
    """ChangeOwnerView: ownership transfer behind owner-only gate."""

    @pytest.fixture
    def animal(self, db, user_profile):
        _, profile = user_profile
        return Animal.objects.create(full_name="OwnerAnimal", owner=profile)

    def test_owner_get_returns_200(self, animal, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).get(f"/pet/{animal.id}/owner/")
        assert response.status_code == 200

    def test_non_owner_get_returns_403(self, animal, second_user_profile, logged_in_client):
        other_user, _ = second_user_profile
        response = logged_in_client(other_user).get(f"/pet/{animal.id}/owner/")
        assert response.status_code == 403

    def test_valid_post_transfers_ownership(self, animal, user_profile, second_user_profile, logged_in_client):
        user, _ = user_profile
        _, new_owner_profile = second_user_profile
        response = logged_in_client(user).post(
            f"/pet/{animal.id}/owner/",
            {"new_owner": new_owner_profile.user.username, "set_keeper": ""},
        )
        assert response.status_code == 302
        animal.refresh_from_db()
        assert animal.owner == new_owner_profile


@pytest.mark.integration
@pytest.mark.django_db
class TestEditShareView:
    """EditShareView: access scope edit behind owner-only gate."""

    @pytest.fixture
    def animal_with_share(self, db, user_profile, second_user_profile):
        _, owner_profile = user_profile
        _, carer_profile = second_user_profile
        animal = Animal.objects.create(full_name="ShareAnimal", owner=owner_profile)
        share = AnimalShare.objects.create(animal=animal, carer=carer_profile)
        return animal, share, carer_profile

    def test_owner_get_returns_200(self, animal_with_share, user_profile, logged_in_client):
        user, _ = user_profile
        animal, _, carer_profile = animal_with_share
        response = logged_in_client(user).get(f"/pet/{animal.id}/keepers/{carer_profile.pk}/access/")
        assert response.status_code == 200

    def test_non_owner_get_returns_403(self, animal_with_share, second_user_profile, logged_in_client):
        other_user, _ = second_user_profile
        animal, _, carer_profile = animal_with_share
        response = logged_in_client(other_user).get(f"/pet/{animal.id}/keepers/{carer_profile.pk}/access/")
        assert response.status_code == 403

    def test_valid_post_updates_share_scope_and_redirects(self, animal_with_share, user_profile, logged_in_client):
        user, _ = user_profile
        animal, share, carer_profile = animal_with_share
        response = logged_in_client(user).post(
            f"/pet/{animal.id}/keepers/{carer_profile.pk}/access/",
            {"allow_basic": "on", "allow_diet": "on"},
        )
        assert response.status_code == 302
        share.refresh_from_db()
        assert share.allow_basic is True
        assert share.allow_diet is True
        assert f"/pet/{animal.id}/tab/ownership/" in response["Location"]


@pytest.mark.integration
@pytest.mark.django_db
class TestMarkDeceasedView:
    """MarkDeceasedView: owner can archive; carer cannot."""

    def test_owner_get_returns_200(self, animal, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).get(f"/pet/{animal.id}/deceased/")
        assert response.status_code == 200

    def test_carer_get_returns_403(self, animal, second_user_profile, logged_in_client):
        other_user, _ = second_user_profile
        response = logged_in_client(other_user).get(f"/pet/{animal.id}/deceased/")
        assert response.status_code == 403

    def test_owner_post_archives_and_redirects(self, animal, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).post(
            f"/pet/{animal.id}/deceased/",
            {"date_of_death": "2024-04-01", "memorial_note": "Goodbye"},
        )
        assert response.status_code == 302
        animal.refresh_from_db()
        assert animal.date_of_death == date(2024, 4, 1)
        assert animal.memorial_note == "Goodbye"

    def test_future_date_rejected(self, animal, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).post(
            f"/pet/{animal.id}/deceased/",
            {"date_of_death": "2099-12-31"},
        )
        assert response.status_code == 200  # form re-render with error


@pytest.mark.integration
@pytest.mark.django_db
class TestUnarchiveAnimalView:
    """UnarchiveAnimalView: owner can un-archive; carer cannot."""

    def test_owner_post_restores_animal(self, deceased_animal, user_profile, logged_in_client):
        user, _ = user_profile
        response = logged_in_client(user).post(f"/pet/{deceased_animal.id}/unarchive/")
        assert response.status_code == 302
        deceased_animal.refresh_from_db()
        assert deceased_animal.date_of_death is None

    def test_carer_post_returns_403(self, deceased_animal, second_user_profile, logged_in_client):
        other_user, _ = second_user_profile
        response = logged_in_client(other_user).post(f"/pet/{deceased_animal.id}/unarchive/")
        assert response.status_code == 403
