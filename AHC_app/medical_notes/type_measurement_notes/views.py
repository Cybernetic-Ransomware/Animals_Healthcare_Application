from django.shortcuts import get_object_or_404
from django.views.generic.edit import FormView

from .forms import BiometricRecordForm
from .models import BiometricRecord, BiometricHeightRecords, BiometricWeightRecords, BiometricCustomRecords
from animals.models import Animal as AnimalProfile
from users.models import Profile as UserProfile


class BiometricRecordCreateView(FormView):
    template_name = 'your_template.html'
    form_class = BiometricRecordForm
    success_url = "/pet/animals/"  # to change to pet's timeline

    def form_valid(self, form):
        record_type = form.cleaned_data['record_type']
        animal_id = self.kwargs.get('animal_id')
        note_id = self.kwargs.get('note_id')

        animal = get_object_or_404(AnimalProfile, id=animal_id)
        related_note = get_object_or_404(UserProfile, id=note_id)

        if record_type == 'weight':
            weight = form.cleaned_data['weight']
            weight_record = BiometricWeightRecords.objects.create(weight=weight)
            biometric_record = BiometricRecord.objects.create(animal=animal, related_note=related_note, weight_biometric_record=weight_record)
        elif record_type == 'height':
            height = form.cleaned_data['height']
            height_record = BiometricHeightRecords.objects.create(height=height)
            biometric_record = BiometricRecord.objects.create(animal=animal, related_note=related_note, height_biometric_record=height_record)
        else:
            custom_name = form.cleaned_data['custom_name']
            custom_value = form.cleaned_data['custom_value']
            custom_unit = form.cleaned_data['custom_unit']
            custom_record = BiometricCustomRecords.objects.create(record_name=custom_name, record_value=custom_value, record_unit=custom_unit)
            biometric_record = BiometricRecord.objects.create(animal=animal, related_note=related_note, custom_biometric_record=custom_record)
        return super().form_valid(form)
