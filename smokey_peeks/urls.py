"""
URL configuration for Smokey Peeks project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path("favicon.ico", RedirectView.as_view(url="/static/main/img/log.png", permanent=True)),
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
]
