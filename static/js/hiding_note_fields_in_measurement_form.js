document.addEventListener('DOMContentLoaded', function() {
    const typeOfEventField = document.getElementById('id_record_type');
    if (!typeOfEventField) return;

    const weightField = document.getElementById('field_weight');
    const weightUnitField = document.getElementById('field_weight_unit_to_present');
    const heightField = document.getElementById('field_height');
    const heightUnitField = document.getElementById('field_height_unit_to_present');
    const customNameField = document.getElementById('field_custom_name');
    const customValueField = document.getElementById('field_custom_value');
    const customUnitField = document.getElementById('field_custom_unit');

    const allOptional = [weightField, weightUnitField, heightField, heightUnitField, customNameField, customValueField, customUnitField];

    function show(...fields) {
        allOptional.forEach(f => { if (f) f.style.display = 'none'; });
        fields.forEach(f => { if (f) f.style.display = 'block'; });
    }

    function handleTypeOfEventChange() {
        const value = typeOfEventField.value;
        if (value === 'weight') {
            show(weightField, weightUnitField);
        } else if (value === 'height') {
            show(heightField, heightUnitField);
        } else if (value === 'custom') {
            show(customNameField, customValueField, customUnitField);
        } else {
            show();
        }
    }

    handleTypeOfEventChange();
    typeOfEventField.addEventListener('change', handleTypeOfEventChange);
});
