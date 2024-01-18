from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, UpdateView

from .forms import ProfileUpdateForm, UserRegisterForm, UserUpdateForm
from .models import Profile


class UserRegisterView(CreateView):
    form_class = UserRegisterForm
    template_name = "users/register.html"
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Account has been created for {form.cleaned_data['username']}!")
        Profile.objects.create(user=self.object)
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
