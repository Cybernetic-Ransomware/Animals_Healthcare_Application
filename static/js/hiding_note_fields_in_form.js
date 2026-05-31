document.addEventListener('DOMContentLoaded', function() {
    const typeOfEventField = document.getElementById('id_type_of_event');
    if (!typeOfEventField) return;

    const participantsField = document.getElementById('field_participants');
    const placeField = document.getElementById('field_place');
    const fulldescriptionField = document.getElementById('field_full_description');
    const eventstartedField = document.getElementById('field_date_event_started');
    const eventendedField = document.getElementById('field_date_event_ended');

    const allOptional = [participantsField, placeField, fulldescriptionField, eventstartedField, eventendedField];

    function show(...fields) {
        allOptional.forEach(f => { if (f) f.style.display = 'none'; });
        fields.forEach(f => { if (f) f.style.display = 'block'; });
    }

    function handleTypeOfEventChange() {
        const value = typeOfEventField.value;
        if (value === 'fast_note') {
            show();
        } else if (value === 'medical_visit') {
            show(participantsField, placeField, fulldescriptionField, eventstartedField);
        } else if (value === 'biometric_record') {
            show(fulldescriptionField, eventstartedField);
        } else if (value === 'diet_note' || value === 'medicament_note') {
            show(fulldescriptionField, eventstartedField, eventendedField);
        } else if (value === 'other_user_note') {
            show(participantsField, placeField, fulldescriptionField, eventstartedField, eventendedField);
        }
    }

    handleTypeOfEventChange();
    typeOfEventField.addEventListener('change', handleTypeOfEventChange);
});
