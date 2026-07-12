"""
Views for Smokey Peeks website.
"""
import mimetypes
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

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

_MAX_UPLOAD_BYTES = 8 * 1024 * 1024
_MAX_ALBUM_PHOTOS = 12
_DASHBOARD_RECENT_DAYS = 7
_RESERVATION_ROW_FIELDS = (
    'id', 'name', 'phone', 'email', 'guests', 'location', 'date', 'time', 'status', 'notes',
)


def _auto_complete_past_reservations(today):
    """Mark confirmed reservations whose date has passed as completed."""
    Reservation.objects.filter(status='confirmed', date__lt=today).update(status='completed')


def _dashboard_reservations_queryset(today):
    """Reservations from the last week through all upcoming dates."""
    from datetime import timedelta

    recent_cutoff = today - timedelta(days=_DASHBOARD_RECENT_DAYS)
    return Reservation.objects.filter(date__gte=recent_cutoff).order_by('-date', '-time')


def _all_reservations_queryset():
    """All reservations for the admin history view."""
    return Reservation.objects.order_by('-date', '-time')


def _format_reservation_row(reservation):
    """Format a reservation for the admin dashboard table."""
    if isinstance(reservation, dict):
        data = reservation
        date_val = data['date']
        time_val = data['time']
    else:
        data = {
            'id': reservation.id,
            'name': reservation.name,
            'phone': reservation.phone,
            'email': reservation.email,
            'guests': reservation.guests,
            'location': reservation.location,
            'date': reservation.date,
            'time': reservation.time,
            'status': reservation.status,
            'notes': reservation.notes,
        }
        date_val = reservation.date
        time_val = reservation.time

    date_str = date_val.strftime('%b %d, %Y') if hasattr(date_val, 'strftime') else str(date_val)
    time_str = time_val.strftime('%I:%M %p') if hasattr(time_val, 'strftime') else str(time_val)
    date_iso = date_val.isoformat() if hasattr(date_val, 'isoformat') else str(date_val)
    time_iso = time_val.strftime('%H:%M') if hasattr(time_val, 'strftime') else str(time_val)[:5]
    location_display = dict(Reservation.LOCATION_CHOICES).get(data.get('location', ''), data.get('location', ''))
    status_display = dict(Reservation.STATUS_CHOICES).get(data['status'], data['status'])

    return {
        **data,
        'date': date_str,
        'date_iso': date_iso,
        'time': time_str,
        'time_iso': time_iso,
        'status_display': status_display,
        'location_display': location_display,
    }


def _build_admin_notifications(limit=15):
    """Build Facebook-style notification payload for the admin header."""
    items = []

    for reservation in Reservation.objects.filter(status='pending').order_by('-created_at'):
        items.append({
            'id': f'res-{reservation.id}',
            'type': 'reservation',
            'title': f'{reservation.name} requested a reservation',
            'message': (
                f'{reservation.guests} guests · '
                f'{reservation.get_location_display()} · '
                f'{reservation.date.strftime("%b %d")}'
            ),
            'href': '#admin-recent-pending',
            'created_at': reservation.created_at.isoformat(),
        })

    for review in CustomerReview.objects.filter(approved=False).order_by('-created_at'):
        preview = review.comment[:80] + ('…' if len(review.comment) > 80 else '')
        items.append({
            'id': f'rev-{review.id}',
            'type': 'review',
            'title': 'New customer review awaiting approval',
            'message': f'{review.email}: {preview}',
            'href': '#admin-reviews-pending',
            'created_at': review.created_at.isoformat(),
        })

    items.sort(key=lambda item: item['created_at'], reverse=True)
    pending_reservations_count = Reservation.objects.filter(status='pending').count()

    return {
        'count': len(items),
        'items': items[:limit],
        'pending_count': pending_reservations_count,
        'all_confirmed': pending_reservations_count == 0,
    }


@require_GET
def serve_media(request, path):
    """Serve uploaded files in production (DEBUG=False)."""
    media_root = Path(settings.MEDIA_ROOT).resolve()
    safe_path = path.replace("\\", "/").lstrip("/")
    full_path = (media_root / safe_path).resolve()
    try:
        full_path.relative_to(media_root)
    except ValueError as exc:
        raise Http404("Invalid media path") from exc
    if not full_path.is_file():
        raise Http404("Media file not found")
    content_type, _ = mimetypes.guess_type(str(full_path))
    return FileResponse(
        full_path.open("rb"),
        content_type=content_type or "application/octet-stream",
    )


def _ensure_session_key(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _build_feed_items(request):
    """Merge approved posts, session-pending uploads, and reviews into one timeline."""
    session_key = _ensure_session_key(request)
    liked_ids = set(
        FeedLike.objects.filter(session_key=session_key).values_list("post_id", flat=True)
    )
    pending_ids = request.session.get("pending_feed_post_ids", [])
    items = []
    seen_post_ids = set()

    for post in FeedPost.objects.filter(approved=True):
        seen_post_ids.add(post.id)
        items.append({
            "kind": "post",
            "obj": post,
            "pinned": post.pinned,
            "date": post.created_at,
            "liked": post.id in liked_ids,
            "pending": False,
        })

    for post in FeedPost.objects.filter(pk__in=pending_ids, approved=False).order_by("-created_at"):
        if post.id in seen_post_ids:
            continue
        items.append({
            "kind": "post",
            "obj": post,
            "pinned": False,
            "date": post.created_at,
            "liked": False,
            "pending": True,
        })

    for review in CustomerReview.objects.filter(approved=True):
        items.append({
            "kind": "review",
            "obj": review,
            "pinned": False,
            "date": review.created_at,
            "liked": False,
            "pending": False,
        })
    items.sort(key=lambda x: (not x["pinned"], -x["date"].timestamp()))
    return items


def _build_feed_albums(request):
    """Approved albums plus this session's pending submissions."""
    pending_ids = request.session.get("pending_album_ids", [])
    seen = set()
    albums = []

    for album in Album.objects.filter(approved=True).prefetch_related("photos"):
        seen.add(album.id)
        albums.append({"obj": album, "pending": False})

    for album in Album.objects.filter(pk__in=pending_ids, approved=False).prefetch_related("photos"):
        if album.id in seen:
            continue
        albums.append({"obj": album, "pending": True})

    return albums


def home(request):
    reviews = CustomerReview.objects.filter(approved=True)[:6]
    return render(request, 'main/homepage.html', {"reviews": reviews})


def feed(request):
    return render(request, "main/feed.html", {
        "feed_items": _build_feed_items(request),
        "albums": _build_feed_albums(request),
    })


@require_POST
def submit_feed_post(request):
    author_name = request.POST.get("author_name", "").strip()
    email = request.POST.get("email", "").strip()
    caption = request.POST.get("caption", "").strip()
    image = request.FILES.get("image")

    if not author_name or not email:
        return JsonResponse({"ok": False, "error": "Name and email are required."}, status=400)
    if not caption and not image:
        return JsonResponse({"ok": False, "error": "Write a message or add a photo before posting."}, status=400)
    if image and image.size > _MAX_UPLOAD_BYTES:
        return JsonResponse({"ok": False, "error": "Photo must be 8 MB or smaller."}, status=400)

    try:
        post = FeedPost.objects.create(
            post_type="customer",
            author_name=author_name,
            email=email,
            caption=caption,
            image=image if image else None,
            approved=False,
        )
        pending_ids = request.session.get("pending_feed_post_ids", [])
        pending_ids.append(post.id)
        request.session["pending_feed_post_ids"] = pending_ids[-20:]
        request.session.modified = True
    except Exception:
        return JsonResponse(
            {"ok": False, "error": "Upload failed. Please try a smaller JPG or PNG photo."},
            status=500,
        )

    return JsonResponse({
        "ok": True,
        "pending": True,
        "post_id": post.id,
        "message": "Post submitted! It will appear here with “Awaiting approval” until management approves it.",
    })


@require_POST
def submit_feed_album(request):
    title = request.POST.get("title", "").strip()
    description = request.POST.get("description", "").strip()
    author_name = request.POST.get("author_name", "").strip()
    email = request.POST.get("email", "").strip()
    photos = request.FILES.getlist("images")

    if not title:
        return JsonResponse({"ok": False, "error": "Album title is required."}, status=400)
    if not author_name or not email:
        return JsonResponse({"ok": False, "error": "Name and email are required."}, status=400)
    if not photos:
        return JsonResponse({"ok": False, "error": "Add at least one photo to your album."}, status=400)
    if len(photos) > _MAX_ALBUM_PHOTOS:
        return JsonResponse(
            {"ok": False, "error": f"You can upload up to {_MAX_ALBUM_PHOTOS} photos per album."},
            status=400,
        )

    for photo in photos:
        if photo.size > _MAX_UPLOAD_BYTES:
            return JsonResponse({"ok": False, "error": "Each photo must be 8 MB or smaller."}, status=400)

    try:
        with transaction.atomic():
            album = Album.objects.create(
                title=title,
                description=description,
                author_name=author_name,
                email=email,
                approved=False,
            )
            for index, photo in enumerate(photos):
                AlbumPhoto.objects.create(
                    album=album,
                    image=photo,
                    sort_order=index,
                )
            pending_ids = request.session.get("pending_album_ids", [])
            pending_ids.append(album.id)
            request.session["pending_album_ids"] = pending_ids[-10:]
            request.session.modified = True
    except Exception:
        return JsonResponse(
            {"ok": False, "error": "Album upload failed. Please try again with smaller JPG or PNG photos."},
            status=500,
        )

    return JsonResponse({
        "ok": True,
        "pending": True,
        "album_id": album.id,
        "message": "Album submitted! It will appear here with “Awaiting approval” until management approves it.",
    })


@require_POST
def feed_like(request, pk):
    post = get_object_or_404(FeedPost, pk=pk, approved=True)
    session_key = _ensure_session_key(request)
    like, created = FeedLike.objects.get_or_create(post=post, session_key=session_key)
    if created:
        FeedPost.objects.filter(pk=post.pk).update(like_count=F("like_count") + 1)
        post.refresh_from_db()
    return JsonResponse({"ok": True, "like_count": post.like_count, "liked": True})


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
        loc = location_map.get(loc, "ilcorso")
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
    now = timezone.localtime()
    today = now.date()
    _auto_complete_past_reservations(today)
    reservations = _dashboard_reservations_queryset(today)
    today_qs = Reservation.objects.filter(created_at__date=today)
    today_count = today_qs.count()
    today_confirmed = today_qs.filter(status='confirmed').count()
    today_pending = today_qs.filter(status='pending').count()
    today_cancelled = today_qs.filter(status='cancelled').count()
    month_qs = Reservation.objects.filter(
        created_at__year=now.year,
        created_at__month=now.month,
        status='confirmed',
    )
    month_count = month_qs.count()
    current_month_name = now.strftime('%B')
    notifications = _build_admin_notifications()
    pending_reservations_count = notifications['pending_count']
    reviews_pending = CustomerReview.objects.filter(approved=False).order_by("-created_at")
    reviews_approved = CustomerReview.objects.filter(approved=True).order_by("-created_at")[:50]
    total_visits = SiteVisitCounter.get_total()
    return render(request, 'main/adminpage.html', {
        'reservations': reservations,
        'today_count': today_count,
        'today_confirmed': today_confirmed,
        'today_pending': today_pending,
        'today_cancelled': today_cancelled,
        'reviews_pending': reviews_pending,
        'reviews_approved': reviews_approved,
        'total_visits': total_visits,
        'month_count': month_count,
        'current_month_name': current_month_name,
        'pending_reservations_count': pending_reservations_count,
        'notification_count': notifications['count'],
        'notification_items': notifications['items'],
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
@require_POST
def admin_approve_feed_post(request, pk):
    post = get_object_or_404(FeedPost, pk=pk)
    if not post.approved:
        post.approved = True
        post.save(update_fields=["approved"])
    return JsonResponse({"ok": True})


@login_required(login_url='main:logadmin')
@require_POST
def admin_remove_feed_post(request, pk):
    post = get_object_or_404(FeedPost, pk=pk)
    post.delete()
    return JsonResponse({"ok": True})


@login_required(login_url='main:logadmin')
@require_POST
def admin_pin_feed_post(request, pk):
    post = get_object_or_404(FeedPost, pk=pk, approved=True)
    post.pinned = True
    post.save(update_fields=["pinned"])
    return JsonResponse({"ok": True})


@login_required(login_url='main:logadmin')
@require_POST
def admin_unpin_feed_post(request, pk):
    post = get_object_or_404(FeedPost, pk=pk)
    post.pinned = False
    post.save(update_fields=["pinned"])
    return JsonResponse({"ok": True})


@login_required(login_url='main:logadmin')
@require_POST
def admin_create_feed_update(request):
    caption = request.POST.get("caption", "").strip()
    image = request.FILES.get("image")
    if not caption and not image:
        return JsonResponse({"ok": False, "error": "Add a message or photo for the update."}, status=400)
    if image and image.size > _MAX_UPLOAD_BYTES:
        return JsonResponse({"ok": False, "error": "Photo must be 8 MB or smaller."}, status=400)
    try:
        FeedPost.objects.create(
            post_type="update",
            author_name="Smokey Peeks",
            caption=caption,
            image=image if image else None,
            approved=True,
            created_by=request.user,
        )
    except Exception:
        return JsonResponse(
            {"ok": False, "error": "Upload failed. Please try a smaller JPG or PNG photo."},
            status=500,
        )
    return JsonResponse({"ok": True, "message": "Update posted to the Feed."})


@login_required(login_url='main:logadmin')
@require_POST
def admin_approve_album(request, pk):
    album = get_object_or_404(Album, pk=pk)
    if not album.approved:
        album.approved = True
        album.save(update_fields=["approved"])
    return JsonResponse({"ok": True})


@login_required(login_url='main:logadmin')
@require_POST
def admin_remove_album(request, pk):
    album = get_object_or_404(Album, pk=pk)
    album.delete()
    return JsonResponse({"ok": True})


@login_required(login_url='main:logadmin')
def admin_reservations_recent_json(request):
    """Return recent/upcoming reservations and stats for the realtime dashboard."""
    from django.utils import timezone

    now = timezone.localtime()
    today = now.date()
    _auto_complete_past_reservations(today)

    today_qs = Reservation.objects.filter(created_at__date=today)
    today_data = {
        'total': today_qs.count(),
        'confirmed': today_qs.filter(status='confirmed').count(),
        'pending': today_qs.filter(status='pending').count(),
        'cancelled': today_qs.filter(status='cancelled').count(),
    }
    month_qs = Reservation.objects.filter(
        created_at__year=now.year,
        created_at__month=now.month,
        status='confirmed',
    )
    month_data = {'total': month_qs.count()}
    notification_data = _build_admin_notifications()

    dashboard_rows = [
        _format_reservation_row(dict(r))
        for r in _dashboard_reservations_queryset(today)
        .values(*_RESERVATION_ROW_FIELDS)
    ]

    upcoming = [
        _format_reservation_row(dict(r))
        for r in Reservation.objects.exclude(status='cancelled')
        .filter(date__gte=today)
        .order_by('date', 'time')[:15]
        .values(*_RESERVATION_ROW_FIELDS)
    ]
    recent_cancelled = [
        _format_reservation_row(dict(r))
        for r in Reservation.objects.filter(status='cancelled')
        .order_by('-created_at')[:15]
        .values(*_RESERVATION_ROW_FIELDS)
    ]
    recent_confirmed = [
        _format_reservation_row(dict(r))
        for r in Reservation.objects.filter(status='confirmed')
        .order_by('-created_at')[:15]
        .values(*_RESERVATION_ROW_FIELDS)
    ]
    recent_pending = [
        _format_reservation_row(dict(r))
        for r in Reservation.objects.filter(status='pending')
        .order_by('-created_at')[:15]
        .values(*_RESERVATION_ROW_FIELDS)
    ]

    return JsonResponse({
        'reservations': dashboard_rows,
        'upcoming': upcoming,
        'recent_cancelled': recent_cancelled,
        'recent_confirmed': recent_confirmed,
        'recent_pending': recent_pending,
        'today': today_data,
        'month': month_data,
        'notification': notification_data,
    })


@login_required(login_url='main:logadmin')
def admin_reservations_all_json(request):
    """Return all reservations for the admin history list."""
    from django.utils import timezone

    today = timezone.localdate()
    _auto_complete_past_reservations(today)
    rows = [
        _format_reservation_row(dict(r))
        for r in _all_reservations_queryset().values(*_RESERVATION_ROW_FIELDS)
    ]
    return JsonResponse({'reservations': rows, 'total': len(rows)})


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
        from django.utils import timezone
        if res.status == "confirmed" and res.date < timezone.localdate():
            res.status = "completed"
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
    from django.utils import timezone

    res = get_object_or_404(Reservation, pk=pk)
    today = timezone.localdate()
    res.status = "completed" if res.date < today else "confirmed"
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
