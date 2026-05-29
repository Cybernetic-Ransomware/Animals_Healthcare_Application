from django.contrib.auth.mixins import UserPassesTestMixin

from ahc.apps.animals.models import Animal


class UserPassesOwnershipTestMixin(UserPassesTestMixin):
    def test_func(self):
        owner = Animal.objects.get(pk=self.kwargs["pk"]).owner
        user = self.request.user.profile

        return user == owner
