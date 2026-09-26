import uuid

from django.db import models


class ContactRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=250)
    phone = models.CharField(max_length=32, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    details = models.CharField(max_length=2500, blank=True, default="")

    class Meta:
        abstract = True
        ordering = ["name"]

    def __str__(self):
        return self.name

    def _structured_fields(self):
        return [self.name, self.phone, self.email]

    def as_contact_text(self):
        lines = [field for field in self._structured_fields() if field]
        if self.details:
            lines.append(self.details)
        return "\n".join(lines)


class Vet(ContactRecord):
    owner = models.ForeignKey("users.Profile", on_delete=models.CASCADE, related_name="vets")


class MedicalPlace(ContactRecord):
    owner = models.ForeignKey("users.Profile", on_delete=models.CASCADE, related_name="medical_places")
    address = models.CharField(max_length=250, blank=True, default="")
    website = models.URLField(blank=True, default="")

    def _structured_fields(self):
        return [self.name, self.phone, self.email, self.address, self.website]
