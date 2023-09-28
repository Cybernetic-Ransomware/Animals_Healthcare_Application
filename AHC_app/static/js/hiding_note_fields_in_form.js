document.addEventListener('DOMContentLoaded', function() {
    function handleTypeOfEventChange() {
        const typeOfEventField = document.getElementById('id_type_of_event');
        const participantsField = document.getElementById('div_id_participants');
        const placeField = document.getElementById('div_id_place');
        const fulldescriptionField = document.getElementById('div_id_full_description');
        const eventstartedField = document.getElementById('div_id_date_event_started');
        const eventendedField = document.getElementById('div_id_date_event_ended');

        if (typeOfEventField.value === 'fast_note') {
            participantsField.style.display = 'none';
            placeField.style.display = 'none';
            fulldescriptionField.style.display = 'none';
            eventstartedField.style.display = 'none';
            eventendedField.style.display = 'none';
        } else if (typeOfEventField.value === 'medical_visit') {
            participantsField.style.display = 'block';
            placeField.style.display = 'block';
            fulldescriptionField.style.display = 'block';
            eventstartedField.style.display = 'block';
            eventendedField.style.display = 'none';
        } else if (typeOfEventField.value === 'biometric_record') {
            participantsField.style.display = 'none';
            placeField.style.display = 'none';
            fulldescriptionField.style.display = 'block';
            eventstartedField.style.display = 'block';
            eventendedField.style.display = 'none';
        } else if (typeOfEventField.value === 'diet_note') {
            participantsField.style.display = 'none';
            placeField.style.display = 'none';
            fulldescriptionField.style.display = 'block';
            eventstartedField.style.display = 'block';
            eventendedField.style.display = 'block';
        } else if (typeOfEventField.value === 'medicament_note') {
            participantsField.style.display = 'none';
            placeField.style.display = 'none';
            fulldescriptionField.style.display = 'block';
            eventstartedField.style.display = 'block';
            eventendedField.style.display = 'block';
        } else if (typeOfEventField.value === 'other_user_note') {
            participantsField.style.display = 'block';
            placeField.style.display = 'block';
            fulldescriptionField.style.display = 'block';
            eventstartedField.style.display = 'block';
            eventendedField.style.display = 'block';
        }
    }

    handleTypeOfEventChange();

    const typeOfEventField = document.getElementById('id_type_of_event');
    typeOfEventField.addEventListener('change', handleTypeOfEventChange);
});
