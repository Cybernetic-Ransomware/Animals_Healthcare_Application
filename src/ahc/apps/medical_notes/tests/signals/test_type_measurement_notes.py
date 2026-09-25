from unittest.mock import MagicMock

import pytest
from django.core.exceptions import ValidationError

from ahc.apps.medical_notes.models.type_measurement_notes import (
    BiometricHeightRecords,
    BiometricWeightRecords,
)
from ahc.apps.medical_notes.signals.type_measurement_notes import validate_one_to_one_fields


def _make_instance(weight=None, height=None, custom=None):
    instance = MagicMock()
    instance.weight_biometric_record = weight
    instance.height_biometric_record = height
    instance.custom_biometric_record = custom
    return instance


@pytest.mark.unit
class TestBiometricRecordValidation:
    """validate_one_to_one_fields: at most one measurement type per BiometricRecord."""

    def test_two_types_raises_validation_error(self):
        instance = _make_instance(
            weight=BiometricWeightRecords(weight=5),
            height=BiometricHeightRecords(height=30),
        )
        with pytest.raises(ValidationError):
            validate_one_to_one_fields(sender=None, instance=instance)

    def test_all_three_types_raises_validation_error(self):
        from ahc.apps.medical_notes.models.type_measurement_notes import BiometricCustomRecords

        instance = _make_instance(
            weight=BiometricWeightRecords(weight=5),
            height=BiometricHeightRecords(height=30),
            custom=BiometricCustomRecords(record_name="x", record_value="1", record_unit="cm"),
        )
        with pytest.raises(ValidationError):
            validate_one_to_one_fields(sender=None, instance=instance)

    def test_weight_only_is_valid(self):
        instance = _make_instance(weight=BiometricWeightRecords(weight=5))
        validate_one_to_one_fields(sender=None, instance=instance)

    def test_height_only_is_valid(self):
        instance = _make_instance(height=BiometricHeightRecords(height=30))
        validate_one_to_one_fields(sender=None, instance=instance)

    def test_all_none_is_valid(self):
        instance = _make_instance()
        validate_one_to_one_fields(sender=None, instance=instance)
