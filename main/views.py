"""
Views for Smokey Peeks website.
"""
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import AdminActivity, CustomerReview, Reservation


def home(request):
    reviews = CustomerReview.objects.filter(approved=True)[:6]
    return render(request, 'main/homepage.html', {"reviews": reviews})


@require_POST
def submit_review(request):
    email = request.POST.get("email", "").strip()
    comment = request.POST.get("comment", "").strip()

    if not email or not comment:
        return JsonResponse({"ok": False, "error": "Email and comment are required."}, status=400)

    CustomerReview.objects.create(email=email, comment=comment)

    return JsonResponse(
        {
            "ok": True,
            "pending": True,
            "message": "Thank you! Your review will appear on the site after an admin approves it.",
        }
    )


def menu(request):
    return render(request, 'main/menu.html')


def location(request):
    return render(request, 'main/location.html')


def reservation(request):
    if request.method == "POST":
        location_map = {
            "onepav": "onepav",
            "ilcorso": "ilcorso",
            "One Pavilion Mall": "onepav",
            "Il Corso South Food Park": "ilcorso",
        }
        loc = request.POST.get("location", "").strip()
        loc = location_map.get(loc, "onepav")
        try:
            email = request.POST.get("email", "").strip()
            Reservation.objects.create(
                location=loc,
                date=request.POST.get("date"),
                time=request.POST.get("time"),
                guests=int(request.POST.get("guests", 2)),
                name=request.POST.get("name", "").strip(),
                email=email,
                phone=request.POST.get("phone", "").strip(),
                notes=request.POST.get("notes", "").strip(),
            )
            messages.success(request, "SUCCESS")
            request.session["reservation_success_email"] = email
            return redirect("main:reservation")
        except (ValueError, TypeError):
            messages.error(request, "Please check your input and try again.")

    reservation_success_email = request.session.pop("reservation_success_email", None) or ""
    return render(request, "main/reservation.html", {"reservation_success_email": reservation_success_email})


def events(request):
    return render(request, 'main/events.html')


def about_us(request):
    return render(request, 'main/aboutus.html')


@login_required(login_url='main:logadmin')
def admin_page(request):
    from django.utils import timezone
    today = timezone.localdate()
    reservations = Reservation.objects.all().order_by('-date', '-time')
    today_qs = Reservation.objects.filter(created_at__date=today)
    today_count = today_qs.count()
    today_confirmed = today_qs.filter(status='confirmed').count()
    today_pending = today_qs.filter(status='pending').count()
    today_cancelled = today_qs.filter(status='cancelled').count()
    reviews_pending = CustomerReview.objects.filter(approved=False).order_by("-created_at")
    reviews_approved = CustomerReview.objects.filter(approved=True).order_by("-created_at")[:50]
    return render(request, 'main/adminpage.html', {
        'reservations': reservations,
        'today_count': today_count,
        'today_confirmed': today_confirmed,
        'today_pending': today_pending,
        'today_cancelled': today_cancelled,
        'reviews_pending': reviews_pending,
        'reviews_approved': reviews_approved,
    })


@login_required(login_url='main:logadmin')
@require_POST
def admin_approve_review(request, pk):
    rev = get_object_or_404(CustomerReview, pk=pk)
    if not rev.approved:
        rev.approved = True
        rev.save()
    return JsonResponse({"ok": True})


@login_required(login_url='main:logadmin')
@require_POST
def admin_remove_review(request, pk):
    rev = get_object_or_404(CustomerReview, pk=pk)
    rev.delete()
    return JsonResponse({"ok": True})


@login_required(login_url='main:logadmin')
def admin_reservations_recent_json(request):
    """Return recent reservations by status for realtime dashboard boxes."""
    def format_reservation(r):
        date_str = r['date'].strftime('%b %d, %Y') if hasattr(r['date'], 'strftime') else str(r['date'])
        time_str = r['time'].strftime('%I:%M %p') if hasattr(r['time'], 'strftime') else str(r['time'])
        location_display = dict(Reservation.LOCATION_CHOICES).get(r.get('location', ''), r.get('location', ''))
        return {
            **r,
            'date': date_str,
            'time': time_str,
            'status_display': dict(Reservation.STATUS_CHOICES).get(r['status'], r['status']),
            'location_display': location_display,
        }

    from django.utils import timezone

    today = timezone.localdate()

    today_qs = Reservation.objects.filter(created_at__date=today)
    today_data = {
        'total': today_qs.count(),
        'confirmed': today_qs.filter(status='confirmed').count(),
        'pending': today_qs.filter(status='pending').count(),
        'cancelled': today_qs.filter(status='cancelled').count(),
    }

    upcoming = [
        format_reservation(dict(r))
        for r in Reservation.objects.exclude(status='cancelled')
        .filter(date__gte=today)
        .order_by('date', 'time')[:15]
        .values('id', 'name', 'phone', 'guests', 'location', 'date', 'time', 'status')
    ]
    recent_cancelled = [
        format_reservation(dict(r))
        for r in Reservation.objects.filter(status='cancelled')
        .order_by('-created_at')[:15]
        .values('id', 'name', 'phone', 'guests', 'location', 'date', 'time', 'status')
    ]
    recent_confirmed = [
        format_reservation(dict(r))
        for r in Reservation.objects.filter(status='confirmed')
        .order_by('-created_at')[:15]
        .values('id', 'name', 'phone', 'guests', 'location', 'date', 'time', 'status')
    ]
    recent_pending = [
        format_reservation(dict(r))
        for r in Reservation.objects.filter(status='pending')
        .order_by('-created_at')[:15]
        .values('id', 'name', 'phone', 'guests', 'location', 'date', 'time', 'status')
    ]

    return JsonResponse({
        'upcoming': upcoming,
        'recent_cancelled': recent_cancelled,
        'recent_confirmed': recent_confirmed,
        'recent_pending': recent_pending,
        'today': today_data,
    })


def log_admin(request):
    if request.user.is_authenticated:
        return redirect('main:admin')
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('main:admin')
        messages.error(request, "Invalid username or password.")
    return render(request, 'main/logadmin.html')


def admin_logout(request):
    logout(request)
    return redirect('main:logadmin')


@login_required(login_url='main:logadmin')
def admin_history(request):
    """Transaction history of admin actions."""
    activities = AdminActivity.objects.select_related("reservation", "admin_user").all()[:200]
    return render(request, "main/historyadmin.html", {"activities": activities})


@login_required(login_url='main:logadmin')
@require_POST
def admin_edit_reservation(request, pk):
    """Update a reservation from the admin dashboard."""
    res = get_object_or_404(Reservation, pk=pk)
    try:
        old_status = res.status
        res.name = request.POST.get("name", res.name).strip()
        res.phone = request.POST.get("phone", res.phone).strip()
        res.email = request.POST.get("email", res.email).strip()
        res.guests = int(request.POST.get("guests", res.guests))
        res.location = request.POST.get("location", res.location)
        date_str = request.POST.get("date")
        time_str = request.POST.get("time")
        if date_str:
            res.date = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
        if time_str:
            t = time_str.strip()
            try:
                res.time = datetime.strptime(t, "%H:%M").time()
            except ValueError:
                res.time = datetime.strptime(t, "%H:%M:%S").time()
        res.status = request.POST.get("status", res.status)
        res.notes = request.POST.get("notes", res.notes).strip()
        res.save()
        action = "cancelled" if res.status == "cancelled" else "edited"
        details = f"Status: {old_status} → {res.status}" if old_status != res.status else "Updated reservation details"
        AdminActivity.objects.create(
            action=action,
            reservation=res,
            reservation_name=res.name,
            details=details,
            admin_user=request.user,
        )
        return JsonResponse({"ok": True})
    except (ValueError, TypeError) as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)


@login_required(login_url='main:logadmin')
@require_POST
def admin_confirm_reservation(request, pk):
    """Set reservation status to confirmed."""
    res = get_object_or_404(Reservation, pk=pk)
    res.status = "confirmed"
    res.save()
    AdminActivity.objects.create(
        action="confirmed",
        reservation=res,
        reservation_name=res.name,
        details="Confirmed reservation",
        admin_user=request.user,
    )
    return JsonResponse({"ok": True})


@login_required(login_url='main:logadmin')
@require_POST
def admin_cancel_reservation(request, pk):
    """Set reservation status to cancelled."""
    res = get_object_or_404(Reservation, pk=pk)
    res.status = "cancelled"
    res.save()
    AdminActivity.objects.create(
        action="cancelled",
        reservation=res,
        reservation_name=res.name,
        details="Cancelled reservation",
        admin_user=request.user,
    )
    return JsonResponse({"ok": True})


def bbq_beer(request):
    return render(request, 'main/bbq-beer.html')


def live_music(request):
    return render(request, 'main/live-music.html')


def live_sports(request):
    return render(request, 'main/live-sports.html')


def merch(request):
    return render(request, 'main/merch.html')
