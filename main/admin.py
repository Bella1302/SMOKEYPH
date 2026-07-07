"""
Django admin configuration for main app.
"""
from django.contrib import admin
from .models import Album, AlbumPhoto, FeedPost, Reservation


class AlbumPhotoInline(admin.TabularInline):
    model = AlbumPhoto
    extra = 1
    fields = ["image", "caption", "sort_order"]


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ["title", "author_name", "approved", "created_at"]
    list_filter = ["approved"]
    search_fields = ["title", "description", "author_name", "email"]
    inlines = [AlbumPhotoInline]


@admin.register(FeedPost)
class FeedPostAdmin(admin.ModelAdmin):
    list_display = ["author_name", "post_type", "approved", "pinned", "like_count", "created_at"]
    list_filter = ["post_type", "approved", "pinned"]
    search_fields = ["author_name", "email", "caption"]


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ["name", "date", "time", "location", "guests", "status", "created_at"]
    list_filter = ["status", "location", "date"]
    search_fields = ["name", "email", "phone"]
    readonly_fields = ["created_at"]
    list_editable = ["status"]
