"""
Models for Smokey Peeks website.
"""
from django.conf import settings
from django.db import models


class Reservation(models.Model):
    """Table reservation submitted by customers."""

    LOCATION_CHOICES = [
        ("onepav", "One Pavilion Mall"),
        ("ilcorso", "Il Corso South Food Park"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
    ]

    location = models.CharField(max_length=50, choices=LOCATION_CHOICES)
    date = models.DateField()
    time = models.TimeField()
    guests = models.PositiveIntegerField(default=2)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Reservation"
        verbose_name_plural = "Reservations"

    def __str__(self):
        return f"{self.name} - {self.date} @ {self.get_location_display()}"


class AdminActivity(models.Model):
    """Log of admin actions on reservations."""

    ACTION_CHOICES = [
        ("confirmed", "Confirmed reservation"),
        ("edited", "Edited reservation"),
        ("cancelled", "Cancelled reservation"),
    ]

    created_at = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_activities",
    )
    reservation_name = models.CharField(max_length=200, blank=True)
    details = models.TextField(blank=True)
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="admin_activities",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Admin Activity"
        verbose_name_plural = "Admin Activities"

    def __str__(self):
        return f"{self.get_action_display()} - {self.reservation_name} at {self.created_at}"


class FeedPost(models.Model):
    """User moment or team update shown on the feed."""

    author_name = models.CharField(max_length=120)
    author_initial = models.CharField(max_length=1, blank=True)
    content = models.TextField()
    is_team_update = models.BooleanField(default=False)
    likes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Feed Post"
        verbose_name_plural = "Feed Posts"

    def __str__(self):
        return f"{self.author_name}: {self.content[:50]}"

    @property
    def avatar_initial(self):
        if self.author_initial:
            return self.author_initial.upper()
        return (self.author_name[:1] or "?").upper()


class Album(models.Model):
    """Photo album displayed in the feed/gallery section."""

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    cover_url = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Album"
        verbose_name_plural = "Albums"

    def __str__(self):
        return self.title

    @property
    def cover_image_url(self):
        from .cloud_media import resolve_cloud_url

        if self.cover_url:
            return resolve_cloud_url(self.cover_url)
        first = self.photos.order_by("sort_order", "id").first()
        return resolve_cloud_url(first.cloud_url) if first else ""


class AlbumPhoto(models.Model):
    """Single photo in an album, stored at a cloud URL."""

    album = models.ForeignKey(
        Album,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    cloud_url = models.CharField(max_length=500)
    caption = models.CharField(max_length=200, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Album Photo"
        verbose_name_plural = "Album Photos"

    def __str__(self):
        return self.caption or self.cloud_url

    @property
    def image_url(self):
        from .cloud_media import resolve_cloud_url

        return resolve_cloud_url(self.cloud_url)
