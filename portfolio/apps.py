from django.apps import AppConfig
from django.db.models.signals import post_migrate


class PortfolioConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "portfolio"
    verbose_name = "Portfolio"

    def ready(self):
        from . import signals  # noqa: F401  (file cleanup)
        from .permissions import ensure_default_groups

        post_migrate.connect(ensure_default_groups, sender=self)
