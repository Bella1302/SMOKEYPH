"""
URL configuration for Smokey Peeks project.
"""
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView

from main.views import serve_media

urlpatterns = [
    path("favicon.ico", RedirectView.as_view(url="/static/main/img/log.png", permanent=True)),
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
    re_path(r"^media/(?P<path>.*)$", serve_media, name="serve_media"),
]
