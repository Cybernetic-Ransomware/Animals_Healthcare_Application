from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.views.generic.edit import FormView

from ahc.apps.users.forms import ProfileUpdateForm, ShareDefaultsForm, UserRegisterForm, UserUpdateForm
from ahc.apps.users.models import Profile


class UserRegisterView(CreateView):
    form_class = UserRegisterForm
    template_name = "users/register.html"
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Account has been created for {form.cleaned_data['username']}!")
        return response


class UserProfileView(LoginRequiredMixin, UpdateView):
    model = Profile
    form_class = UserUpdateForm
    template_name = "users/profile.html"
    success_url = reverse_lazy("profile")

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["profile_update"] = ProfileUpdateForm(instance=self.request.user.profile)
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Your profile has been updated")
        return response


class ShareDefaultsView(LoginRequiredMixin, FormView):
    """Let the owner configure their default share scope for new keepers."""

    template_name = "users/share_defaults.html"
    form_class = ShareDefaultsForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        from ahc.apps.animals.selectors import get_or_create_share_defaults

        kwargs["instance"] = get_or_create_share_defaults(self.request.user.profile)
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Default share settings saved.")
        return redirect(reverse("share_defaults"))
