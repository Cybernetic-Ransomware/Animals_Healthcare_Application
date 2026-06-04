document.addEventListener('DOMContentLoaded', function () {
    var recordTypeField = document.getElementById('id_record_type');
    if (!recordTypeField) return;

    var unitRow = document.getElementById('field_unit');
    var customNameRow = document.getElementById('field_custom_name');
    var customUnitRow = document.getElementById('field_custom_unit');

    function toggleSessionFields() {
        var type = recordTypeField.value;
        if (type === 'custom') {
            if (unitRow) unitRow.style.display = 'none';
            if (customNameRow) customNameRow.style.display = 'block';
            if (customUnitRow) customUnitRow.style.display = 'block';
        } else {
            if (unitRow) unitRow.style.display = 'block';
            if (customNameRow) customNameRow.style.display = 'none';
            if (customUnitRow) customUnitRow.style.display = 'none';
        }
    }

    toggleSessionFields();
    recordTypeField.addEventListener('change', toggleSessionFields);
});
