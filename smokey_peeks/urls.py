"""
URL configuration for Smokey Peeks project.
"""
import os

from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView

from main.views import serve_media

urlpatterns = [
    path("favicon.ico", RedirectView.as_view(url="/static/main/img/log.png", permanent=True)),
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
]

# Local disk storage: Django's static.serve returns 404 when DEBUG=False (production).
if not os.environ.get("CLOUDINARY_URL"):
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve_media, name="serve_media"),
    ]
