"""
Views for Smokey Peeks website.
"""
import mimetypes
from datetime import datetime
from pathlib import Path
from django.conf import settings
from django.db.models import F
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone
from .models import AdminActivity, CustomerReview, FeedLike, FeedPost, Reservation, SiteVisitCounter


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

    for post in FeedPost.objects.filter(approved=False).order_by('-created_at'):
        author = post.author_name or post.email or 'Customer'
        preview = post.caption[:80] + ('…' if len(post.caption) > 80 else '') if post.caption else 'New feed submission'
        items.append({
            'id': f'feed-{post.id}',
            'type': 'feed',
            'title': f'New feed post from {author}',
            'message': preview,
            'href': '#admin-feed-pending',
            'created_at': post.created_at.isoformat(),
        })

    items.sort(key=lambda item: item['created_at'], reverse=True)
    pending_reservations_count = Reservation.objects.filter(status='pending').count()
    total_count = len(items)

    return {
        'count': total_count,
        'items': items[:limit],
        'pending_count': pending_reservations_count,
        'all_confirmed': pending_reservations_count == 0,
    }


@require_GET
def serve_media(request, path):
    """Serve uploaded files in production (Django's static.serve refuses when DEBUG=False)."""
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


def home(request):
    reviews = CustomerReview.objects.filter(approved=True)[:6]
    return render(request, 'main/homepage.html', {"reviews": reviews})


def feed(request):
    return render(request, "main/feed.html", {"feed_items": _build_feed_items(request)})


@require_POST
def submit_feed_post(request):
    import json
    import time

    def _debug_log(message, data=None, hypothesis_id="H1"):
        # #region agent log
        try:
            payload = {
                "sessionId": "5b3a1b",
                "runId": "feed-upload",
                "hypothesisId": hypothesis_id,
                "location": "main/views.py:submit_feed_post",
                "message": message,
                "data": data or {},
                "timestamp": int(time.time() * 1000),
            }
            with open(
                Path(__file__).resolve().parent.parent.parent / "debug-5b3a1b.log",
                "a",
                encoding="utf-8",
            ) as fh:
                fh.write(json.dumps(payload) + "\n")
        except OSError:
            pass
        # #endregion

    author_name = request.POST.get("author_name", "").strip()
    email = request.POST.get("email", "").strip()
    caption = request.POST.get("caption", "").strip()
    image = request.FILES.get("image")

    _debug_log("submit_feed_post called", {
        "has_name": bool(author_name),
        "has_email": bool(email),
        "has_image": bool(image),
        "image_size": getattr(image, "size", 0),
    }, "H1")

    if not author_name or not email:
        _debug_log("validation failed missing identity", hypothesis_id="H2")
        return JsonResponse({"ok": False, "error": "Name and email are required."}, status=400)
    if not caption and not image:
        _debug_log("validation failed empty post", hypothesis_id="H2")
        return JsonResponse({"ok": False, "error": "Write a message or add a photo before posting."}, status=400)
    if image and image.size > 8 * 1024 * 1024:
        _debug_log("validation failed image too large", {"size": image.size}, "H2")
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
        _debug_log("post created", {"post_id": post.id, "approved": post.approved}, "H3")
    except Exception as exc:
        _debug_log("post create failed", {"error": str(exc)}, "H4")
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
    reservations = Reservation.objects.all().order_by('-date', '-time')
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
    # #region agent log
    try:
        import json
        from pathlib import Path
        _log_path = Path(__file__).resolve().parent.parent.parent / 'debug-628fad.log'
        _server_order = list(
            reservations.values('id', 'date', 'time', 'status', 'created_at')[:10]
        )
        for _row in _server_order:
            _row['date'] = _row['date'].isoformat()
            _row['time'] = _row['time'].isoformat()
            _row['created_at'] = _row['created_at'].isoformat()
        with open(_log_path, 'a', encoding='utf-8') as _f:
            _f.write(json.dumps({
                'sessionId': '628fad',
                'runId': 'pre-fix',
                'hypothesisId': 'A',
                'location': 'views.py:admin_page',
                'message': 'Server reservation order before template render',
                'data': {
                    'total_count': reservations.count(),
                    'first_ten': _server_order,
                    'order_by': '-date,-time',
                },
                'timestamp': int(now.timestamp() * 1000),
            }) + '\n')
    except Exception:
        pass
    # #endregion
    current_month_name = now.strftime('%B')
    notifications = _build_admin_notifications()
    pending_reservations_count = notifications['pending_count']
    reviews_pending = CustomerReview.objects.filter(approved=False).order_by("-created_at")
    reviews_approved = CustomerReview.objects.filter(approved=True).order_by("-created_at")[:50]
    feed_pending = FeedPost.objects.filter(approved=False).order_by("-created_at")
    feed_approved = FeedPost.objects.filter(approved=True).order_by("-pinned", "-created_at")[:50]
    total_visits = SiteVisitCounter.get_total()
    return render(request, 'main/adminpage.html', {
        'reservations': reservations,
        'today_count': today_count,
        'today_confirmed': today_confirmed,
        'today_pending': today_pending,
        'today_cancelled': today_cancelled,
        'reviews_pending': reviews_pending,
        'reviews_approved': reviews_approved,
        'feed_pending': feed_pending,
        'feed_approved': feed_approved,
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
    FeedPost.objects.create(
        post_type="update",
        author_name="Smokey Peeks",
        caption=caption,
        image=image,
        approved=True,
        created_by=request.user,
    )
    return JsonResponse({"ok": True, "message": "Update posted to the Feed."})


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

    now = timezone.localtime()
    today = now.date()

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
    # #region agent log
    try:
        import json
        from pathlib import Path
        _all_month = Reservation.objects.filter(
            created_at__year=now.year,
            created_at__month=now.month,
        ).count()
        _log_path = Path(__file__).resolve().parent.parent.parent / 'debug-0292ec.log'
        with open(_log_path, 'a', encoding='utf-8') as _f:
            _f.write(json.dumps({
                'sessionId': '0292ec',
                'runId': 'month-confirmed',
                'hypothesisId': 'M1',
                'location': 'views.py:admin_reservations_recent_json',
                'message': 'Monthly JSON reservation counts',
                'data': {
                    'all_statuses': _all_month,
                    'confirmed_only': month_data['total'],
                    'month': now.month,
                    'year': now.year,
                },
                'timestamp': int(now.timestamp() * 1000),
            }) + '\n')
    except Exception:
        pass
    # #endregion
    notification_data = _build_admin_notifications()

    upcoming = [
        format_reservation(dict(r))
        for r in Reservation.objects.exclude(status='cancelled')
        .filter(date__gte=today)
        .order_by('date', 'time')[:15]
        .values('id', 'name', 'phone', 'guests', 'location', 'date', 'time', 'status', 'notes')
    ]
    recent_cancelled = [
        format_reservation(dict(r))
        for r in Reservation.objects.filter(status='cancelled')
        .order_by('-created_at')[:15]
        .values('id', 'name', 'phone', 'guests', 'location', 'date', 'time', 'status', 'notes')
    ]
    recent_confirmed = [
        format_reservation(dict(r))
        for r in Reservation.objects.filter(status='confirmed')
        .order_by('-created_at')[:15]
        .values('id', 'name', 'phone', 'guests', 'location', 'date', 'time', 'status', 'notes')
    ]
    recent_pending = [
        format_reservation(dict(r))
        for r in Reservation.objects.filter(status='pending')
        .order_by('-created_at')[:15]
        .values('id', 'name', 'phone', 'guests', 'location', 'date', 'time', 'status', 'notes')
    ]
    # #region agent log
    try:
        import json
        from pathlib import Path
        _log_path = Path(__file__).resolve().parent.parent.parent / 'debug-628fad.log'
        with open(_log_path, 'a', encoding='utf-8') as _f:
            _f.write(json.dumps({
                'sessionId': '628fad',
                'runId': 'pre-fix',
                'hypothesisId': 'C',
                'location': 'views.py:admin_reservations_recent_json',
                'message': 'Recent box counts vs total available',
                'data': {
                    'returned_upcoming': len(upcoming),
                    'returned_confirmed': len(recent_confirmed),
                    'returned_pending': len(recent_pending),
                    'returned_cancelled': len(recent_cancelled),
                    'total_confirmed': Reservation.objects.filter(status='confirmed').count(),
                    'total_pending': Reservation.objects.filter(status='pending').count(),
                    'total_cancelled': Reservation.objects.filter(status='cancelled').count(),
                    'limit': 15,
                },
                'timestamp': int(now.timestamp() * 1000),
            }) + '\n')
    except Exception:
        pass
    # #endregion

    return JsonResponse({
        'upcoming': upcoming,
        'recent_cancelled': recent_cancelled,
        'recent_confirmed': recent_confirmed,
        'recent_pending': recent_pending,
        'today': today_data,
        'month': month_data,
        'notification': notification_data,
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
