from animals.models import Animal
from django.conf import settings
from django.db.models import Q
from django.views.generic import TemplateView


class HomepageView(TemplateView):
    template_name = "homepage/homepage.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # recent_animals = Animal.objects.order_by('-creation_date').values('id', 'full_name', 'profile_image')[:3]
        # recent_animals = Animal.objects.order_by('-creation_date').values('id', 'full_name', 'profile_image__url')[:3]

        # do przemyślenia dekorator odnośnie niezalogowanego użytkownika

        if not self.request.user.is_authenticated:
            return context

        query = Animal.objects.filter(
            Q(owner=self.request.user.profile)
            | Q(allowed_users=self.request.user.profile)
        ).order_by("-creation_date")

        context["recent_animals"] = query[:3]

        if query and settings.DEBUG:
            context["example_animal_id"] = query.latest("creation_date").id

        return context
