"""
Django admin configuration for main app.
"""
from django.contrib import admin
from .models import (
    AdminActivity,
    Album,
    AlbumPhoto,
    CustomerReview,
    FeedLike,
    FeedPost,
    Reservation,
    SiteVisitCounter,
)


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


@admin.register(CustomerReview)
class CustomerReviewAdmin(admin.ModelAdmin):
    list_display = ["email", "approved", "created_at"]
    list_filter = ["approved"]
    search_fields = ["email", "comment"]


@admin.register(FeedLike)
class FeedLikeAdmin(admin.ModelAdmin):
    list_display = ["post", "session_key", "created_at"]
    readonly_fields = ["post", "session_key", "created_at"]


@admin.register(AdminActivity)
class AdminActivityAdmin(admin.ModelAdmin):
    list_display = ["action", "reservation_name", "admin_user", "created_at"]
    list_filter = ["action"]
    readonly_fields = ["created_at", "action", "reservation", "reservation_name", "details", "admin_user"]


@admin.register(SiteVisitCounter)
class SiteVisitCounterAdmin(admin.ModelAdmin):
    list_display = ["total_visits"]
