"""
URL configuration for minichat project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="chat:room_list"), name="home"),
    path("admin/", admin.site.urls),
    path("users/", include("apps.users.urls")),
    path("chat/", include("apps.chat.urls")),
]

# Debug Toolbar (개발 환경에서만)
if settings.DEBUG:
    try:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
