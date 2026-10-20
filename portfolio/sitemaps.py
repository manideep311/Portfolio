from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Project
from .pages import PAGES


class StaticSitemap(Sitemap):
    changefreq = "monthly"

    def items(self):
        return [page.url_name for page in PAGES]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return 1.0 if item == "portfolio:home" else 0.8


class ProjectSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return Project.objects.published()

    def lastmod(self, obj):
        return obj.updated_at
