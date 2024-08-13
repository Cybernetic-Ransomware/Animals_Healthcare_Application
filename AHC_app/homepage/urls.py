from django.urls import path

from AHC_app.homepage.views import HomepageView

urlpatterns = [
    path("", HomepageView.as_view(), name="Homepage"),
]
