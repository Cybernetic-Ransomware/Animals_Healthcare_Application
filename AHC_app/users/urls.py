from django.contrib import admin
from django.urls import path

from .views import LoginView


urlpatterns = [
    path('login/', LoginView.as_view(template_name='users/login.html'), name='login'),
    # path('logout/', auth_views.LogoutView.as_view(template_name='users/logout.html'), name='logout'),
    # path('register/', user_views.register, name='register'),
    # path('profile/', user_views.profile, name='profile'),
]
