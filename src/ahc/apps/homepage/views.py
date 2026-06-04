from django.views.generic import TemplateView

from ahc.apps.animals.selectors import animals_visible_to
from ahc.apps.users.models import Profile as UserProfile


class HomepageView(TemplateView):
    template_name = "homepage/homepage.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user

        if not user.is_authenticated:
            return context

        user_query = UserProfile.objects.get(user=user)
        profile = user.profile

        if user_query.allow_recennt_animals_list:
            # Deceased animals are excluded: pinned_animals may contain a now-deceased
            # animal so we filter explicitly; animals_visible_to already excludes deceased.
            context["pinned_animals"] = user_query.pinned_animals.filter(date_of_death__isnull=True)
            context["recent_animals"] = animals_visible_to(profile).order_by("-creation_date")[:3]

        return context
