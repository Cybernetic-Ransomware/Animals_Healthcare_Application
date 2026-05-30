document.addEventListener('DOMContentLoaded', function() {
    function handleTypeOfEventChange() {
        const typeOfEventField = document.getElementById('id_record_type');
        const weightField = document.getElementById('div_id_weight');
        const weightUnitField = document.getElementById('div_id_weight_unit_to_present');
        const heightField = document.getElementById('div_id_height');
        const heightUnitField = document.getElementById('div_id_height_unit_to_present');
        const customNameField = document.getElementById('div_id_custom_name');
        const customValueField = document.getElementById('div_id_custom_value');
        const customUnitField = document.getElementById('div_id_custom_unit');

        const selectedRecordType = typeOfEventField.value;

        weightField.style.display = 'none';
        weightUnitField.style.display = 'none';
        heightField.style.display = 'none';
        heightUnitField.style.display = 'none';
        customNameField.style.display = 'none';
        customValueField.style.display = 'none';
        customUnitField.style.display = 'none';

        if (selectedRecordType === 'weight') {
            weightField.style.display = 'block';
            weightUnitField.style.display = 'block';
        } else if (selectedRecordType === 'height') {
            heightField.style.display = 'block';
            heightUnitField.style.display = 'block';
        } else if (selectedRecordType === 'custom') {
            customNameField.style.display = 'block';
            customValueField.style.display = 'block';
            customUnitField.style.display = 'block';
        }
    }

    handleTypeOfEventChange();

    const typeOfEventField = document.getElementById('id_record_type');
    typeOfEventField.addEventListener('change', handleTypeOfEventChange);
});
