from django.contrib.auth.mixins import UserPassesTestMixin

from ahc.apps.animals.models import Animal
from ahc.apps.animals.selectors import is_animal_owner


class UserPassesOwnershipTestMixin(UserPassesTestMixin):
    def test_func(self):
        animal = Animal.objects.get(pk=self.kwargs["pk"])
        return is_animal_owner(self.request.user.profile, animal)
