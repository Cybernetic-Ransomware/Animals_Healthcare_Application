// Conditional field visibility for MedicalRecordForm.
// Exposed as window.initNoteForm so modal.js can re-run it after htmx swaps.

(function () {
    "use strict";

    function handleTypeOfEventChange() {
        var typeOfEventField = document.getElementById('id_type_of_event');
        if (!typeOfEventField) return;

        var participantsField = document.getElementById('field_participants');
        var placeField = document.getElementById('field_place');
        var fulldescriptionField = document.getElementById('field_full_description');
        var eventstartedField = document.getElementById('field_date_event_started');
        var eventendedField = document.getElementById('field_date_event_ended');

        var allOptional = [participantsField, placeField, fulldescriptionField, eventstartedField, eventendedField];

        function show() {
            var fields = Array.from(arguments);
            allOptional.forEach(function (f) { if (f) f.style.display = 'none'; });
            fields.forEach(function (f) { if (f) f.style.display = 'block'; });
        }

        var value = typeOfEventField.value;
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

    window.initNoteForm = function initNoteForm() {
        var typeOfEventField = document.getElementById('id_type_of_event');
        if (!typeOfEventField) return;
        handleTypeOfEventChange();
        typeOfEventField.addEventListener('change', handleTypeOfEventChange);
    };

    document.addEventListener('DOMContentLoaded', window.initNoteForm);
}());
