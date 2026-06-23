"""
Models for Smokey Peeks website.
"""
from django.conf import settings
from django.db import models
from django.db.models import F


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


class CustomerReview(models.Model):
    """Customer reviews shown on the homepage."""

    email = models.EmailField()
    comment = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Customer Review"
        verbose_name_plural = "Customer Reviews"

    def __str__(self):
        return f"{self.email} at {self.created_at}"


class FeedPost(models.Model):
    """Customer photos and management updates shown on the Feed page."""

    POST_TYPE_CHOICES = [
        ("customer", "Customer Experience"),
        ("update", "Management Update"),
    ]

    post_type = models.CharField(max_length=20, choices=POST_TYPE_CHOICES, default="customer")
    author_name = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    caption = models.TextField(max_length=1000, blank=True)
    image = models.ImageField(upload_to="feed/%Y/%m/", blank=True, null=True)
    approved = models.BooleanField(default=False)
    pinned = models.BooleanField(default=False)
    like_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feed_posts",
    )

    class Meta:
        ordering = ["-pinned", "-created_at"]
        verbose_name = "Feed Post"
        verbose_name_plural = "Feed Posts"

    def __str__(self):
        label = self.author_name or self.email or "Post"
        return f"{label} ({self.get_post_type_display()})"


class FeedLike(models.Model):
    """One heart per browser session per post."""

    post = models.ForeignKey(FeedPost, on_delete=models.CASCADE, related_name="likes")
    session_key = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["post", "session_key"], name="unique_feed_like_per_session"),
        ]

    def __str__(self):
        return f"Like on post {self.post_id}"


class SiteVisitCounter(models.Model):
    """Singleton counter for website visits (one count per session)."""

    total_visits = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Site Visit Counter"
        verbose_name_plural = "Site Visit Counter"

    @classmethod
    def get_total(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj.total_visits

    @classmethod
    def increment(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        cls.objects.filter(pk=1).update(total_visits=F("total_visits") + 1)
        obj.refresh_from_db()
        return obj.total_visits
