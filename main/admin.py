"""
Django admin configuration for main app.
"""
from django.contrib import admin
from .models import Album, AlbumPhoto, FeedPost, Reservation


class AlbumPhotoInline(admin.TabularInline):
    model = AlbumPhoto
    extra = 1
    fields = ["cloud_url", "caption", "sort_order"]


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ["title", "created_at"]
    search_fields = ["title", "description"]
    inlines = [AlbumPhotoInline]


@admin.register(FeedPost)
class FeedPostAdmin(admin.ModelAdmin):
    list_display = ["author_name", "is_team_update", "likes", "created_at"]
    list_filter = ["is_team_update"]
    search_fields = ["author_name", "content"]


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ["name", "date", "time", "location", "guests", "status", "created_at"]
    list_filter = ["status", "location", "date"]
    search_fields = ["name", "email", "phone"]
    readonly_fields = ["created_at"]
    list_editable = ["status"]
