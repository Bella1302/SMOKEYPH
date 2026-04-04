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
