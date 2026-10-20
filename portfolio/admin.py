from django.contrib import admin, messages
from django.db.models import Count
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.text import Truncator

from .models import (
    Achievement,
    Certification,
    ContactMessage,
    Education,
    Experience,
    ExperienceLink,
    Principle,
    Project,
    ProjectImage,
    SiteProfile,
    Skill,
    SkillCategory,
    SocialLink,
)

admin.site.site_header = "Manideep's Notebook"
admin.site.site_title = "Notebook CMS"
admin.site.index_title = "Manage the portfolio"


def thumbnail(file, alt="", size=64):
    if not file:
        return format_html('<span class="nb-thumb nb-thumb--empty" aria-hidden="true">✎</span>')
    try:
        url = file.url
    except ValueError:
        return "—"
    return format_html(
        '<img src="{}" alt="{}" class="nb-thumb" width="{}" height="{}" loading="lazy" style="object-fit:cover">',
        url,
        alt,
        size,
        round(size * 0.75),
    )


# ---------------------------------------------------------------------------
# Profile (singleton)
# ---------------------------------------------------------------------------
@admin.register(SiteProfile)
class SiteProfileAdmin(admin.ModelAdmin):
    readonly_fields = ("portrait_preview", "updated_at")
    fieldsets = (
        ("Identity", {"fields": ("name", "role", "focus", "location", "availability")}),
        ("Hero copy", {"fields": ("headline", "intro", "education_line")}),
        ("About", {"fields": ("about",)}),
        ("Portrait", {"fields": ("portrait", "portrait_preview", "portrait_alt", "portrait_film_look")}),
        ("Contact & résumé", {"fields": ("email", "phone", "show_phone", "resume")}),
        ("Search & sharing", {"fields": ("seo_description", "updated_at")}),
    )

    @admin.display(description="Current portrait")
    def portrait_preview(self, obj):
        return thumbnail(obj.portrait, obj.portrait_alt, size=160)

    def has_add_permission(self, request):
        return super().has_add_permission(request) and not SiteProfile.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        profile = SiteProfile.load()
        if profile:
            return redirect(reverse("admin:portfolio_siteprofile_change", args=[profile.pk]))
        return redirect(reverse("admin:portfolio_siteprofile_add"))


@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = ("label", "kind", "url", "is_visible", "order")
    list_editable = ("is_visible", "order")
    list_filter = ("kind", "is_visible")
    search_fields = ("label", "url")


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 2
    fields = ("preview", "image", "alt_text", "caption", "order")
    readonly_fields = ("preview",)
    ordering = ("order", "pk")
    verbose_name = "screenshot"
    verbose_name_plural = "Screenshots — upload as many as you like; lower order shows first"

    @admin.display(description="Preview")
    def preview(self, obj):
        return thumbnail(obj.image, obj.alt_text, size=96)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "cover",
        "title",
        "status",
        "is_featured",
        "order",
        "year",
        "screenshots",
        "live_badge",
        "updated_at",
    )
    list_display_links = ("cover", "title")
    list_editable = ("status", "is_featured", "order")
    list_filter = ("status", "is_featured", "art", "year")
    search_fields = ("title", "slug", "tagline", "summary", "description", "technologies")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("cover_preview", "created_at", "updated_at")
    inlines = [ProjectImageInline]
    save_on_top = True
    actions = ["publish", "unpublish", "feature", "unfeature"]
    list_per_page = 25
    fieldsets = (
        ("The basics", {"fields": ("title", "slug", "year", "tagline", "summary")}),
        (
            "The story",
            {
                "fields": ("description", "contribution", "outcomes", "technologies", "note"),
                "description": "Write it like a case study: what it is, what you built, what happened.",
            },
        ),
        (
            "Cover & look",
            {"fields": ("featured_image", "cover_preview", "featured_image_alt", "art", "accent")},
        ),
        ("Links", {"fields": ("live_url", "github_url", "extra_link_label", "extra_link_url")}),
        (
            "Publishing",
            {
                "fields": ("status", "is_featured", "order", "published_at", "created_at", "updated_at"),
                "description": "Only published projects are visible publicly. Featured + published projects appear on the homepage.",
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(screenshot_total=Count("images"))

    @admin.display(description="", ordering=None)
    def cover(self, obj):
        first = obj.featured_image or next((img.image for img in obj.images.all()[:1]), None)
        return thumbnail(first, obj.featured_image_alt)

    @admin.display(description="Cover preview")
    def cover_preview(self, obj):
        return thumbnail(obj.featured_image, obj.featured_image_alt, size=220)

    @admin.display(description="Shots", ordering="screenshot_total")
    def screenshots(self, obj):
        return obj.screenshot_total

    @admin.display(description="Public?")
    def live_badge(self, obj):
        if obj.is_live:
            return format_html(
                '<a class="nb-badge nb-badge--live" href="{}" target="_blank" rel="noopener">live ↗</a>',
                obj.get_absolute_url(),
            )
        if obj.status == Project.Status.PUBLISHED:
            return format_html('<span class="nb-badge">scheduled</span>')
        return format_html(
            '<a class="nb-badge" href="{}" target="_blank" rel="noopener">preview ↗</a>', obj.get_absolute_url()
        )

    @admin.action(description="Publish selected projects", permissions=["change"])
    def publish(self, request, queryset):
        now = timezone.now()
        count = 0
        for project in queryset:
            project.status = Project.Status.PUBLISHED
            if project.published_at is None or project.published_at > now:
                project.published_at = now
            project.save(update_fields=["status", "published_at", "updated_at"])
            count += 1
        self.message_user(request, f"Published {count} project(s).", messages.SUCCESS)

    @admin.action(description="Move selected projects back to draft", permissions=["change"])
    def unpublish(self, request, queryset):
        count = queryset.update(status=Project.Status.DRAFT, updated_at=timezone.now())
        self.message_user(request, f"{count} project(s) are drafts again and hidden from the site.", messages.SUCCESS)

    @admin.action(description="Feature on homepage", permissions=["change"])
    def feature(self, request, queryset):
        count = queryset.update(is_featured=True, updated_at=timezone.now())
        self.message_user(
            request, f"Featured {count} project(s). Remember: only published projects are shown.", messages.SUCCESS
        )

    @admin.action(description="Remove from homepage", permissions=["change"])
    def unfeature(self, request, queryset):
        count = queryset.update(is_featured=False, updated_at=timezone.now())
        self.message_user(request, f"Removed {count} project(s) from the homepage.", messages.SUCCESS)


# ---------------------------------------------------------------------------
# Skills, experience, credentials
# ---------------------------------------------------------------------------
class SkillInline(admin.TabularInline):
    model = Skill
    extra = 1
    fields = ("name", "is_minor", "order")


@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "style", "skill_count", "order")
    list_editable = ("order",)
    search_fields = ("title", "skills__name")
    inlines = [SkillInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(skill_total=Count("skills"))

    @admin.display(description="Skills", ordering="skill_total")
    def skill_count(self, obj):
        return obj.skill_total


class ExperienceLinkInline(admin.TabularInline):
    model = ExperienceLink
    extra = 1
    fields = ("label", "url", "order")


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ("role", "organization", "start_date", "end_date", "is_published", "order")
    list_editable = ("is_published", "order")
    list_filter = ("is_published",)
    search_fields = ("role", "organization", "highlights")
    inlines = [ExperienceLinkInline]


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ("degree", "field", "institution", "start_date", "end_date", "score", "order")
    list_editable = ("order",)
    search_fields = ("degree", "field", "institution")


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ("name", "issuer", "has_link", "order")
    list_editable = ("order",)
    list_filter = ("issuer",)
    search_fields = ("name", "issuer")

    @admin.display(boolean=True, description="Link")
    def has_link(self, obj):
        return bool(obj.url)


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("title", "detail", "order")
    list_editable = ("order",)
    search_fields = ("title", "detail")


@admin.register(Principle)
class PrincipleAdmin(admin.ModelAdmin):
    list_display = ("title", "order")
    list_editable = ("order",)


# ---------------------------------------------------------------------------
# Private inbox — visible only to staff with the contact message permissions
# ---------------------------------------------------------------------------
@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "excerpt", "created_at", "is_read")
    list_filter = ("is_read", "created_at")
    search_fields = ("name", "email", "message")
    date_hierarchy = "created_at"
    readonly_fields = ("name", "email", "message", "created_at", "notified", "reply_link")
    fields = ("name", "email", "reply_link", "message", "created_at", "notified", "is_read")
    actions = ["mark_read", "mark_unread"]

    @admin.display(description="Message")
    def excerpt(self, obj):
        return Truncator(obj.message).chars(80)

    @admin.display(description="Reply")
    def reply_link(self, obj):
        return format_html('<a href="mailto:{}?subject=Re:%20your%20message">Reply by email ↗</a>', obj.email)

    def has_add_permission(self, request):
        return False

    def change_view(self, request, object_id, form_url="", extra_context=None):
        if request.method == "GET" and self.has_change_permission(request):
            ContactMessage.objects.filter(pk=object_id, is_read=False).update(is_read=True)
        return super().change_view(request, object_id, form_url, extra_context)

    @admin.action(description="Mark as read", permissions=["change"])
    def mark_read(self, request, queryset):
        queryset.update(is_read=True)

    @admin.action(description="Mark as unread", permissions=["change"])
    def mark_unread(self, request, queryset):
        queryset.update(is_read=False)
