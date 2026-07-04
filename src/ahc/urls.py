"""
URL configuration for AHC_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("ahc.apps.homepage.urls")),
    path("user/", include("ahc.apps.users.urls")),
    path("pet/", include("ahc.apps.animals.urls")),
    path("pet/<uuid:pk>/offline-snapshot/", include("ahc.apps.offline_snapshots.urls")),
    path("note/", include("ahc.apps.medical_notes.urls")),
    path(
        "favicon.ico",
        RedirectView.as_view(url=f"{settings.MEDIA_URL}icons/chinchilla.png"),
    ),
    path("media/<path:path>", serve, {"document_root": settings.MEDIA_ROOT}),
]
