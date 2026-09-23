from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.views.generic.edit import FormView

from ahc.apps.users.forms import ProfileUpdateForm, ShareDefaultsForm, UserRegisterForm, UserUpdateForm
from ahc.apps.users.models import Profile

if TYPE_CHECKING:
    from ahc.types import AuthenticatedRequest


class UserRegisterView(CreateView):
    form_class = UserRegisterForm
    template_name = "users/register.html"
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Account has been created for {form.cleaned_data['username']}!")
        return response


class UserProfileView(LoginRequiredMixin, UpdateView):
    """Binds, validates, and saves the User and Profile forms as one atomic submit."""

    model = Profile
    request: AuthenticatedRequest
    form_class = UserUpdateForm
    template_name = "users/profile.html"
    success_url = reverse_lazy("profile")

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("profile_update", ProfileUpdateForm(instance=self.request.user.profile))
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)

        user_valid = form.is_valid()
        profile_valid = profile_form.is_valid()
        if user_valid and profile_valid:
            return self._save_both_forms(form, profile_form)
        return self.render_to_response(self.get_context_data(form=form, profile_update=profile_form))

    def _save_both_forms(self, form, profile_form):
        with transaction.atomic():
            response = super().form_valid(form)
            profile_form.save()
        messages.success(self.request, "Your profile has been updated")
        return response


class ShareDefaultsView(LoginRequiredMixin, FormView):
    """Let the owner configure their default share scope for new keepers."""

    template_name = "users/share_defaults.html"
    form_class = ShareDefaultsForm
    request: AuthenticatedRequest

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        from ahc.apps.animals.selectors import get_or_create_share_defaults

        kwargs["instance"] = get_or_create_share_defaults(self.request.user.profile)
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Default share settings saved.")
        return redirect(reverse("share_defaults"))
