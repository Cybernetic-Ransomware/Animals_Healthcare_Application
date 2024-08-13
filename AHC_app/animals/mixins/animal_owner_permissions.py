from animals.models import Animal
from django.contrib.auth.mixins import UserPassesTestMixin


class UserPassesOwnershipTestMixin(UserPassesTestMixin):
    def test_func(self):
        owner = Animal.objects.get(pk=self.kwargs["pk"]).owner
        user = self.request.user.profile

        return user == owner
