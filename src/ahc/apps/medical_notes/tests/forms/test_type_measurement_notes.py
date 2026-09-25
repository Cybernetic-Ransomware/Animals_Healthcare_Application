import pytest


@pytest.mark.unit
class TestBiometricRecordForm:
    """BiometricRecordForm: decimal weight/height, and conditional-required fields."""

    @pytest.mark.regression
    def test_weight_accepts_decimal_input(self):
        """Regression #61: a decimal weight was rejected by an IntegerField."""
        from decimal import Decimal

        from ahc.apps.medical_notes.forms.type_measurement_notes import BiometricRecordForm

        form = BiometricRecordForm(data={"record_type": "weight", "weight": "4.25", "weight_unit_to_present": "kg"})
        assert form.is_valid()
        assert form.cleaned_data["weight"] == Decimal("4.25")

    @pytest.mark.regression
    def test_height_accepts_decimal_input(self):
        """Regression #61: a decimal height was rejected by an IntegerField."""
        from decimal import Decimal

        from ahc.apps.medical_notes.forms.type_measurement_notes import BiometricRecordForm

        form = BiometricRecordForm(data={"record_type": "height", "height": "31.5", "height_unit_to_present": "cm"})
        assert form.is_valid()
        assert form.cleaned_data["height"] == Decimal("31.5")

    def test_weight_accepts_integer_input(self):
        from decimal import Decimal

        from ahc.apps.medical_notes.forms.type_measurement_notes import BiometricRecordForm

        form = BiometricRecordForm(data={"record_type": "weight", "weight": "4", "weight_unit_to_present": "kg"})
        assert form.is_valid()
        assert form.cleaned_data["weight"] == Decimal("4")

    def test_height_accepts_integer_input(self):
        from decimal import Decimal

        from ahc.apps.medical_notes.forms.type_measurement_notes import BiometricRecordForm

        form = BiometricRecordForm(data={"record_type": "height", "height": "31", "height_unit_to_present": "cm"})
        assert form.is_valid()
        assert form.cleaned_data["height"] == Decimal("31")

    def test_weight_rejects_too_many_decimal_places(self):
        from ahc.apps.medical_notes.forms.type_measurement_notes import BiometricRecordForm

        form = BiometricRecordForm(data={"record_type": "weight", "weight": "4.2567", "weight_unit_to_present": "kg"})
        assert not form.is_valid()
        assert "weight" in form.errors
        assert len(form.errors["weight"]) == 1
        assert "required" not in form.errors["weight"][0]

    def test_weight_rejects_too_many_total_digits(self):
        from ahc.apps.medical_notes.forms.type_measurement_notes import BiometricRecordForm

        form = BiometricRecordForm(data={"record_type": "weight", "weight": "123456.789", "weight_unit_to_present": "kg"})
        assert not form.is_valid()
        assert "weight" in form.errors
        assert len(form.errors["weight"]) == 1
        assert "required" not in form.errors["weight"][0]

    def test_custom_value_is_unaffected_by_decimal_change(self):
        from ahc.apps.medical_notes.forms.type_measurement_notes import BiometricRecordForm

        form = BiometricRecordForm(
            data={
                "record_type": "custom",
                "custom_name": "Temperature",
                "custom_value": "4.25",
                "custom_unit": "C",
            }
        )
        assert form.is_valid()
        assert form.cleaned_data["custom_value"] == "4.25"

    def test_weight_record_without_weight_is_invalid(self):
        from ahc.apps.medical_notes.forms.type_measurement_notes import BiometricRecordForm

        form = BiometricRecordForm(data={"record_type": "weight", "weight_unit_to_present": "kg"})
        assert not form.is_valid()
        assert "weight" in form.errors

    def test_height_record_without_height_is_invalid(self):
        from ahc.apps.medical_notes.forms.type_measurement_notes import BiometricRecordForm

        form = BiometricRecordForm(data={"record_type": "height", "height_unit_to_present": "cm"})
        assert not form.is_valid()
        assert "height" in form.errors

    def test_custom_record_without_any_field_is_invalid(self):
        from ahc.apps.medical_notes.forms.type_measurement_notes import BiometricRecordForm

        form = BiometricRecordForm(data={"record_type": "custom"})
        assert not form.is_valid()
        assert "custom_name" in form.errors
        assert "custom_value" in form.errors
        assert "custom_unit" in form.errors

    def test_custom_record_partially_filled_is_invalid(self):
        from ahc.apps.medical_notes.forms.type_measurement_notes import BiometricRecordForm

        form = BiometricRecordForm(data={"record_type": "custom", "custom_name": "Temperature"})
        assert not form.is_valid()
        assert "custom_value" in form.errors
        assert "custom_unit" in form.errors
        assert "custom_name" not in form.errors

    def test_weight_record_with_value_is_still_valid(self):
        from ahc.apps.medical_notes.forms.type_measurement_notes import BiometricRecordForm

        form = BiometricRecordForm(data={"record_type": "weight", "weight": "4.25", "weight_unit_to_present": "kg"})
        assert form.is_valid()
        assert not form.errors

    @pytest.mark.regression
    def test_weight_record_with_blank_unit_is_invalid(self):
        """Regression #61: a weight record without a unit passed validation."""
        from ahc.apps.medical_notes.forms.type_measurement_notes import BiometricRecordForm

        form = BiometricRecordForm(data={"record_type": "weight", "weight": "4.25", "weight_unit_to_present": ""})
        assert not form.is_valid()
        assert "weight_unit_to_present" in form.errors
        assert "weight" not in form.errors

    @pytest.mark.regression
    def test_height_record_with_blank_unit_is_invalid(self):
        """Regression #61: a height record without a unit passed validation."""
        from ahc.apps.medical_notes.forms.type_measurement_notes import BiometricRecordForm

        form = BiometricRecordForm(data={"record_type": "height", "height": "31.5", "height_unit_to_present": ""})
        assert not form.is_valid()
        assert "height_unit_to_present" in form.errors
        assert "height" not in form.errors

    def test_weight_record_with_zero_value_is_valid(self):
        from decimal import Decimal

        from ahc.apps.medical_notes.forms.type_measurement_notes import BiometricRecordForm

        form = BiometricRecordForm(data={"record_type": "weight", "weight": "0", "weight_unit_to_present": "kg"})
        assert form.is_valid()
        assert form.cleaned_data["weight"] == Decimal("0")
