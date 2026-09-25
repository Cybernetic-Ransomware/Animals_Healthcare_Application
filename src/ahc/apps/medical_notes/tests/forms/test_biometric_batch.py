import uuid

import pytest

from ahc.apps.medical_notes.forms.biometric_batch import BiometricBatchRowForm, BiometricBatchSessionForm


@pytest.mark.unit
class TestBiometricBatchRowForm:
    """BiometricBatchRowForm: include+value cross-field validation."""

    def test_checked_row_without_value_is_invalid(self):
        form = BiometricBatchRowForm(data={"include": True, "animal_id": str(uuid.uuid4()), "value": ""})
        assert not form.is_valid()
        assert "value" in form.errors

    def test_unchecked_row_without_value_is_valid(self):
        form = BiometricBatchRowForm(data={"include": False, "animal_id": str(uuid.uuid4()), "value": ""})
        assert form.is_valid()

    def test_checked_row_with_value_is_valid(self):
        form = BiometricBatchRowForm(data={"include": True, "animal_id": str(uuid.uuid4()), "value": "12.500"})
        assert form.is_valid()


@pytest.mark.unit
class TestBiometricBatchSessionForm:
    """BiometricBatchSessionForm: custom type requires name and unit."""

    def test_custom_type_without_name_and_unit_is_invalid(self):
        form = BiometricBatchSessionForm(data={"record_type": "custom", "unit": "", "custom_name": "", "custom_unit": ""})
        assert not form.is_valid()
        assert "custom_name" in form.errors
        assert "custom_unit" in form.errors

    def test_weight_type_without_unit_is_valid(self):
        form = BiometricBatchSessionForm(data={"record_type": "weight", "unit": "", "custom_name": "", "custom_unit": ""})
        assert form.is_valid()
