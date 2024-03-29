from django.contrib.auth import views as auth_views
from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.urls import path

from . import views as user_views

urlpatterns = [
    path("", auth_views.LoginView.as_view(template_name="users/login.html"), name="login"),
    path("login/", auth_views.LoginView.as_view(template_name="users/login.html"), name="login"),
    path("register/", user_views.UserRegisterView.as_view(), name="register"),
    path("login_success/", auth_views.LoginView.as_view(template_name="users/login_success.html"), name="login_success"),
    path("logout/", auth_views.LogoutView.as_view(template_name="users/logout.html"), name="logout"),
    path("profile/", user_views.UserProfileView.as_view(), name="profile"),
    path("password-reset/", PasswordResetView.as_view(template_name="users/password_reset.html", html_email_template_name="users/password_reset_email.html"), name="password-reset"),
    path("password-reset/done/", PasswordResetDoneView.as_view(template_name="users/password_reset_done.html"), name="password_reset_done"),
    path("password-reset-confirm/<uidb64>/<token>/", PasswordResetConfirmView.as_view(template_name="users/password_reset_confirm.html"), name="password_reset_confirm"),
    path("password-reset-complete/", PasswordResetCompleteView.as_view(template_name="users/password_reset_complete.html"), name="password_reset_complete"),
]
