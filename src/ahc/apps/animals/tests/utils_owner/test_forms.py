import pytest

from ahc.apps.animals.utils_owner.forms import ChangeFirstContactForm


@pytest.mark.unit
class TestChangeFirstContactFormLabels:
    @pytest.mark.regression
    def test_labels_stay_pre_c4_user_facing_text(self):
        """Regression (C4 review): legacy_* is an internal expand/contract detail, not a user-facing label."""
        form = ChangeFirstContactForm()
        assert form.fields["legacy_first_contact_vet"].label == "First contact vet"
        assert form.fields["legacy_first_contact_medical_place"].label == "First contact medical place"
