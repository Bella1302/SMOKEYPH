"""
Signals for main app.
"""
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Reservation


@receiver(pre_save, sender=Reservation)
def send_confirmation_email_on_status_change(sender, instance, raw, **kwargs):
    """Send confirmation email when admin marks reservation as confirmed."""
    if raw:
        return
    old_status = None
    if instance.pk:
        try:
            old = Reservation.objects.get(pk=instance.pk)
            old_status = old.status
        except Reservation.DoesNotExist:
            pass
    if old_status != "confirmed" and instance.status == "confirmed":
        try:
            send_mail(
                subject="Your Smokey Peeks Reservation is Confirmed!",
                message=(
                    f"Hi {instance.name},\n\n"
                    f"Great news! Your reservation has been confirmed.\n\n"
                    f"Details:\n"
                    f"- Date: {instance.date}\n"
                    f"- Time: {instance.time}\n"
                    f"- Location: {instance.get_location_display()}\n"
                    f"- Guests: {instance.guests}\n\n"
                    f"We look forward to seeing you at Smokey Peeks!\n\n"
                    f"For questions, call 0967 586 7197 or 0977 654 4225."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.email],
                fail_silently=False,
            )
        except Exception:
            pass
