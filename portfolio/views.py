import hashlib
import logging

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import connection
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET, require_http_methods

from .forms import ContactForm
from .models import (
    Achievement,
    Certification,
    Education,
    Experience,
    Principle,
    Project,
    SkillCategory,
)

logger = logging.getLogger(__name__)


def _education_context():
    education = list(Education.objects.all())
    return {"education": education, "current_education": next((e for e in education if e.in_progress), None)}


def home(request):
    return render(request, "portfolio/home.html", {**_education_context(), "address": "hello"})


def about(request):
    context = {
        **_education_context(),
        "principles": Principle.objects.all(),
        "achievements": Achievement.objects.all(),
        "address": "about",
    }
    return render(request, "portfolio/about.html", context)


def toolkit(request):
    context = {"skill_categories": SkillCategory.objects.prefetch_related("skills"), "address": "toolkit"}
    return render(request, "portfolio/toolkit.html", context)


def journey(request):
    context = {
        **_education_context(),
        "experience": Experience.objects.filter(is_published=True).prefetch_related("links"),
        "certifications": Certification.objects.all(),
        "achievements": Achievement.objects.all(),
        "address": "journey",
    }
    return render(request, "portfolio/journey.html", context)


def project_list(request):
    # Featured projects lead the Work page; the rest follow in their usual order.
    projects = Project.objects.published().order_by("-is_featured", "order", "-published_at", "pk").prefetch_related("images")
    return render(request, "portfolio/project_list.html", {"projects": projects, "address": "work"})


def project_detail(request, slug):
    project = get_object_or_404(Project.objects.prefetch_related("images"), slug=slug)
    is_preview = False
    if not project.is_live:
        # Drafts and scheduled projects exist only for signed-in staff who may view them.
        if not (request.user.is_active and request.user.is_staff and request.user.has_perm("portfolio.view_project")):
            raise Http404("Project not found")
        is_preview = True

    published = list(Project.objects.published().only("slug", "title", "order", "published_at"))
    index = next((i for i, p in enumerate(published) if p.pk == project.pk), None)
    previous_project = next_project = None
    if index is not None and len(published) > 1:
        previous_project = published[index - 1] if index > 0 else None
        next_project = published[index + 1] if index + 1 < len(published) else None

    response = render(
        request,
        "portfolio/project_detail.html",
        {
            "project": project,
            "screenshots": project.images.all(),
            "is_preview": is_preview,
            "previous_project": previous_project,
            "next_project": next_project,
            "address": f"work/{project.slug}",
        },
    )
    if is_preview:
        response["X-Robots-Tag"] = "noindex, nofollow"
        response["Cache-Control"] = "private, no-store"
    return response


def _client_fingerprint(request) -> str:
    ip = request.META.get("REMOTE_ADDR", "")
    if settings.TRUST_X_FORWARDED_FOR:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
    return hashlib.sha256(f"{ip}{settings.SECRET_KEY}".encode()).hexdigest()[:32]


def _rate_limited(request) -> bool:
    key = f"contact-rate:{_client_fingerprint(request)}"
    added = cache.add(key, 1, timeout=settings.CONTACT_RATE_WINDOW_SECONDS)
    if added:
        return False
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=settings.CONTACT_RATE_WINDOW_SECONDS)
        return False
    return count > settings.CONTACT_RATE_LIMIT


def _notify(message) -> None:
    recipient = settings.CONTACT_NOTIFY_EMAIL
    if not recipient:
        return
    try:
        send_mail(
            subject=f"New portfolio message from {message.name}",
            message=f"From: {message.name} <{message.email}>\n\n{message.message}\n\nRead it in the admin.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
    except Exception:  # The message is safely stored either way.
        logger.exception("Could not send contact notification email")
        return
    message.notified = True
    message.save(update_fields=["notified"])


@require_http_methods(["GET", "POST"])
def contact(request):
    if request.method == "GET":
        return render(request, "portfolio/contact.html", {"contact_form": ContactForm(), "address": "contact"})

    form = ContactForm(request.POST)
    if form.is_spam:
        # Pretend everything worked so bots learn nothing.
        return redirect("portfolio:contact_thanks")

    if _rate_limited(request):
        form.add_error(None, "That's a lot of messages in a short time. Please try again later or email me directly.")
        return render(request, "portfolio/contact.html", {"contact_form": form, "address": "contact"}, status=429)

    if not form.is_valid():
        return render(request, "portfolio/contact.html", {"contact_form": form, "address": "contact"}, status=400)

    message = form.save()
    _notify(message)
    return redirect("portfolio:contact_thanks")


def contact_thanks(request):
    return render(request, "portfolio/contact_thanks.html")


@require_GET
@cache_control(max_age=86400, public=True)
def robots_txt(request):
    base = settings.SITE_URL or request.build_absolute_uri("/").rstrip("/")
    lines = ["User-agent: *", "Allow: /", "", f"Sitemap: {base}{reverse('sitemap')}"]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


@require_GET
def healthz(request):
    connection.ensure_connection()
    return HttpResponse("ok", content_type="text/plain")


def page_not_found(request, exception=None):
    return render(request, "404.html", status=404)
