from django.conf import settings

from .models import SiteProfile, SocialLink


def site(request):
    """Profile + links for every template (two tiny queries, cached per request)."""
    if not hasattr(request, "_site_context"):
        profile = SiteProfile.load()
        request._site_context = {
            "profile": profile,
            "social_links": list(SocialLink.objects.filter(is_visible=True)),
            "site_url": settings.SITE_URL or request.build_absolute_uri("/").rstrip("/"),
        }
    return request._site_context
