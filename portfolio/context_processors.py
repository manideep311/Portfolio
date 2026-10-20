from django.conf import settings

from .models import SiteProfile, SocialLink
from .pages import page_context


def site(request):
    """Profile + links for every template (two tiny queries, cached per request)."""
    if not hasattr(request, "_site_context"):
        profile = SiteProfile.load()
        request._site_context = {
            "profile": profile,
            "social_links": list(SocialLink.objects.filter(is_visible=True)),
            "site_url": settings.SITE_URL or request.build_absolute_uri("/").rstrip("/"),
        }
    match = getattr(request, "resolver_match", None)
    return {**request._site_context, **page_context(match.url_name if match else None)}
