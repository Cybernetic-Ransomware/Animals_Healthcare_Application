from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import redirect
from django.views.generic import TemplateView

from animals.models import Animal


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

    def send_email(self):
        recipient_email = 'scorpos6@gmail.com'
        subject = 'Test subject'
        message = 'Test message'
        sender_email = None

        send_mail(subject, message, sender_email, [recipient_email], fail_silently=True)

    def post(self, request, *args, **kwargs):
        if 'send_email' in request.POST:
            self.send_email()
            self.extra_context = {'email_sent': True}
            return redirect(request.path)
        return super().post(request, *args, **kwargs)
