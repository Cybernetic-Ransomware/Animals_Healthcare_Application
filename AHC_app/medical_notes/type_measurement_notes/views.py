from django.shortcuts import get_object_or_404, reverse, redirect
from django.views.generic.edit import FormView

from .forms import BiometricRecordForm
from .models import BiometricRecord, BiometricHeightRecords, BiometricWeightRecords, BiometricCustomRecords
from animals.models import Animal as AnimalProfile
from medical_notes.models import MedicalRecord


class BiometricRecordCreateView(FormView):
    template_name = 'medical_notes/create.html'
    form_class = BiometricRecordForm

    def form_valid(self, form):
        record_type = form.cleaned_data['record_type']
        animal_id = self.kwargs.get('pk')
        note_id = self.kwargs.get('note_id')

        animal = get_object_or_404(AnimalProfile, id=animal_id)
        print(f'{note_id=}')
        related_note = get_object_or_404(MedicalRecord, id=note_id)
        print(f'{related_note=}')

        if record_type == 'weight':
            weight = form.cleaned_data['weight']
            unit = form.cleaned_data['weight_unit_to_present']
            weight_record = BiometricWeightRecords.objects.create(weight=weight, weight_unit_to_present=unit)
            biometric_record = BiometricRecord.objects.create(animal=animal, related_note=related_note, weight_biometric_record=weight_record)
        elif record_type == 'height':
            height = form.cleaned_data['height']
            unit = form.cleaned_data['height_unit_to_present']
            height_record = BiometricHeightRecords.objects.create(height=height, height_unit_to_present=unit)
            biometric_record = BiometricRecord.objects.create(animal=animal, related_note=related_note, height_biometric_record=height_record)
        else:
            custom_name = form.cleaned_data['custom_name']
            custom_value = form.cleaned_data['custom_value']
            custom_unit = form.cleaned_data['custom_unit']
            custom_record = BiometricCustomRecords.objects.create(record_name=custom_name, record_value=custom_value, record_unit=custom_unit)
            biometric_record = BiometricRecord.objects.create(animal=animal, related_note=related_note, custom_biometric_record=custom_record)

        success_url = reverse("animal_profile", kwargs={"pk": animal_id})
        return redirect(success_url)
