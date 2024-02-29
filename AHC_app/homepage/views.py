from animals.models import Animal
from django.db.models import Q
from django.views.generic import TemplateView
from users.models import Profile as UserProfile


class HomepageView(TemplateView):
    template_name = "homepage/homepage.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user

        if not user.is_authenticated:
            return context

        user_query = UserProfile.objects.get(user=user)

        if user_query.allow_recennt_animals_list:
            pinned_animals_query = user_query.pinned_animals.all()

            context["pinned_animals"] = pinned_animals_query

        if user_query.allow_recennt_animals_list:

            recent_created_animals_query = Animal.objects.filter(
                Q(owner=self.request.user.profile) | Q(allowed_users=self.request.user.profile)
            ).order_by("-creation_date")[:3]

            context["recent_animals"] = recent_created_animals_query

        return context
