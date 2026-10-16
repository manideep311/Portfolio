from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, re_path
from django.views.static import serve

from portfolio import views
from portfolio.sitemaps import ProjectSitemap, StaticSitemap

sitemaps = {"static": StaticSitemap, "projects": ProjectSitemap}

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("robots.txt", views.robots_txt, name="robots_txt"),
    path("healthz/", views.healthz, name="healthz"),
    path("", include("portfolio.urls")),
]

# Local media in development. In production prefer object storage; set
# SERVE_MEDIA=true only when media lives on a persistent disk (see README).
if settings.DEBUG or getattr(settings, "SERVE_MEDIA", False):
    media_prefix = settings.MEDIA_URL.lstrip("/")
    if not media_prefix.startswith("http"):
        urlpatterns += [re_path(rf"^{media_prefix}(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT})]

handler404 = "portfolio.views.page_not_found"
