from animals.models import Animal
from django.db.models import Q
from django.views.generic import TemplateView


class HomepageView(TemplateView):
    template_name = "homepage/homepage.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if not self.request.user.is_authenticated:
            return context

        query = Animal.objects.filter(
            Q(owner=self.request.user.profile) | Q(allowed_users=self.request.user.profile)
        ).order_by("-creation_date")

        context["recent_animals"] = query[:3]

        return context
