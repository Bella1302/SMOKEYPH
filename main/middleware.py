"""Track unique website visits (one per browser session)."""

from .models import SiteVisitCounter


class VisitCounterMiddleware:
    SKIP_PREFIXES = ("/static/", "/media/", "/admin-dashboard/", "/admin/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if not any(path.startswith(prefix) for prefix in self.SKIP_PREFIXES):
            if not request.session.get("visit_counted"):
                SiteVisitCounter.increment()
                request.session["visit_counted"] = True
        return self.get_response(request)
