"""
Cloud media URL helpers for album and gallery assets.
"""
from django.conf import settings


def resolve_cloud_url(url_or_path: str) -> str:
    """Return a full cloud URL from an absolute URL or a path under CLOUD_MEDIA_BASE_URL."""
    url_or_path = (url_or_path or "").strip()
    if not url_or_path:
        return ""
    if url_or_path.startswith(("http://", "https://")):
        return url_or_path
    base = getattr(settings, "CLOUD_MEDIA_BASE_URL", "").rstrip("/")
    if not base:
        return url_or_path
    return f"{base}/{url_or_path.lstrip('/')}"
