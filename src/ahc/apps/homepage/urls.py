from django.urls import path

from ahc.apps.homepage.views import HomepageView

urlpatterns = [
    path("", HomepageView.as_view(), name="Homepage"),
]
