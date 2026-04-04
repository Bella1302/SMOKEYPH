"""
URL configuration for main app.
"""
from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.home, name='home'),
    path('reviews/submit/', views.submit_review, name='submit_review'),
    path('menu/', views.menu, name='menu'),
    path('location/', views.location, name='location'),
    path('reservation/', views.reservation, name='reservation'),
    path('events/', views.events, name='events'),
    path('about/', views.about_us, name='about'),
    path('admin-dashboard/', views.admin_page, name='admin'),
    path('admin-dashboard/history/', views.admin_history, name='admin_history'),
    path('admin-dashboard/reservations-recent.json', views.admin_reservations_recent_json, name='admin_reservations_recent_json'),
    path('admin-dashboard/review/<int:pk>/approve/', views.admin_approve_review, name='admin_approve_review'),
    path('logadmin/', views.log_admin, name='logadmin'),
    path('admin-logout/', views.admin_logout, name='admin_logout'),
    path('admin-dashboard/reservation/<int:pk>/edit/', views.admin_edit_reservation, name='admin_edit_reservation'),
    path('admin-dashboard/reservation/<int:pk>/confirm/', views.admin_confirm_reservation, name='admin_confirm_reservation'),
    path('admin-dashboard/reservation/<int:pk>/cancel/', views.admin_cancel_reservation, name='admin_cancel_reservation'),
    path('bbq-beer/', views.bbq_beer, name='bbq_beer'),
    path('live-music/', views.live_music, name='live_music'),
    path('live-sports/', views.live_sports, name='live_sports'),
    path('merch/', views.merch, name='merch'),
]
