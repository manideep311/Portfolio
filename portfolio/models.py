import uuid
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from .film import film_look
from .images import optimise_image_field
from .validators import (
    ALLOWED_IMAGE_EXTENSIONS,
    validate_document_size,
    validate_hex_color,
    validate_image_content,
    validate_image_size,
    validate_pdf,
)

IMAGE_VALIDATORS = [
    FileExtensionValidator(ALLOWED_IMAGE_EXTENSIONS),
    validate_image_size,
    validate_image_content,
]
IMAGE_HELP = "JPEG, PNG or WebP. Re-encoded to WebP automatically. Max size set by MAX_IMAGE_UPLOAD_MB (default 8 MB)."


def _unique_name(folder: str, filename: str) -> str:
    extension = Path(filename).suffix.lower() or ".bin"
    return f"{folder}/{uuid.uuid4().hex}{extension}"


def project_cover_path(instance, filename):
    return _unique_name(f"projects/{instance.slug or 'draft'}", filename)


def project_screenshot_path(instance, filename):
    slug = instance.project.slug if instance.project_id else "draft"
    return _unique_name(f"projects/{slug}/screenshots", filename)


def portrait_path(instance, filename):
    return _unique_name("profile", filename)


def resume_path(instance, filename):
    return f"resume/{uuid.uuid4().hex[:10]}/{slugify(Path(filename).stem) or 'resume'}.pdf"


class OrderedModel(models.Model):
    order = models.PositiveIntegerField(
        "display order", default=0, db_index=True, help_text="Lower numbers appear first."
    )

    class Meta:
        abstract = True
        ordering = ["order", "pk"]


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# Profile (singleton)
# ---------------------------------------------------------------------------
class SiteProfile(TimeStampedModel):
    """The identity card: one row, edited from the admin."""

    name = models.CharField(max_length=120)
    role = models.CharField("professional title", max_length=120)
    focus = models.CharField(max_length=160, blank=True, help_text="e.g. NLP, LLMs & Applied Machine Learning")
    headline = models.CharField(max_length=220, help_text="One confident sentence shown large in the hero.")
    intro = models.TextField(help_text="Two or three sentences under the headline.")
    location = models.CharField(max_length=120, blank=True)
    availability = models.CharField(
        max_length=80,
        blank=True,
        help_text="Shown as a stamp in the hero, e.g. 'Open to Gen AI / ML roles'. Leave empty to hide it.",
    )
    about = models.TextField(
        "about story",
        blank=True,
        help_text="Paragraphs separated by a blank line. Shown in the About section.",
    )
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    show_phone = models.BooleanField(default=False, help_text="Publish the phone number on the website.")
    portrait = models.ImageField(
        upload_to=portrait_path,
        blank=True,
        validators=IMAGE_VALIDATORS,
        width_field="portrait_width",
        height_field="portrait_height",
        help_text=IMAGE_HELP,
    )
    portrait_width = models.PositiveIntegerField(null=True, blank=True, editable=False)
    portrait_height = models.PositiveIntegerField(null=True, blank=True, editable=False)
    portrait_alt = models.CharField("portrait alt text", max_length=200, blank=True)
    portrait_film_look = models.BooleanField(
        "notebook film look",
        default=True,
        help_text="Give new portrait uploads the site's instant-film treatment: warm tone, grain, paper texture "
        "and a soft vignette. Applied when a portrait is uploaded.",
    )
    resume = models.FileField(
        "résumé (PDF)",
        upload_to=resume_path,
        blank=True,
        validators=[FileExtensionValidator(["pdf"]), validate_document_size, validate_pdf],
        help_text="PDF only. Max size set by MAX_DOCUMENT_UPLOAD_MB (default 10 MB).",
    )
    seo_description = models.CharField(
        "search description",
        max_length=200,
        blank=True,
        help_text="Used for the meta description and social previews.",
    )
    education_line = models.CharField(max_length=200, blank=True, help_text="Short line under the intro.")

    class Meta:
        verbose_name = "profile"
        verbose_name_plural = "profile"

    def __str__(self):
        return self.name

    @property
    def first_name(self) -> str:
        return self.name.split(" ")[0] if self.name else ""

    @property
    def last_name(self) -> str:
        return " ".join(self.name.split(" ")[1:])

    @property
    def initials(self) -> str:
        return "".join(part[0] for part in self.name.split()[:2]).upper()

    @property
    def about_paragraphs(self) -> list[str]:
        return [p.strip() for p in self.about.split("\n\n") if p.strip()]

    def clean(self):
        if not self.pk and SiteProfile.objects.exists():
            raise ValidationError("There is already a profile. Edit the existing one instead.")
        if self.portrait and not self.portrait_alt:
            raise ValidationError({"portrait_alt": "Describe the portrait for screen-reader users."})

    def save(self, *args, **kwargs):
        optimise_image_field(self, "portrait", max_edge=1200, transform=film_look if self.portrait_film_look else None)
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "SiteProfile | None":
        return cls.objects.order_by("pk").first()


class SocialLink(OrderedModel):
    class Kind(models.TextChoices):
        LINKEDIN = "linkedin", "LinkedIn"
        GITHUB = "github", "GitHub"
        PORTFOLIO = "portfolio", "Website"
        X = "x", "X / Twitter"
        KAGGLE = "kaggle", "Kaggle"
        HUGGINGFACE = "huggingface", "Hugging Face"
        OTHER = "other", "Other"

    label = models.CharField(max_length=60)
    url = models.URLField()
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.OTHER)
    is_visible = models.BooleanField("visible", default=True)

    class Meta(OrderedModel.Meta):
        verbose_name = "social link"

    def __str__(self):
        return self.label


# ---------------------------------------------------------------------------
# Skills, experience, education, credentials
# ---------------------------------------------------------------------------
class SkillCategory(OrderedModel):
    class Icon(models.TextChoices):
        SPARK = "spark", "Spark (generative AI)"
        BRAIN = "brain", "Network (machine learning)"
        BRACES = "braces", "Braces (languages)"
        PIPE = "pipe", "Pipeline (data & MLOps)"
        CLOUD = "cloud", "Cloud (dev & cloud)"
        SIGMA = "sigma", "Sigma (mathematics)"

    class Style(models.TextChoices):
        STICKERS = "stickers", "Stickers on an index card"
        TAGS = "tags", "Tags on graph paper"
        KEYS = "keys", "Typewriter keys"
        PIPELINE = "pipeline", "Connected pipeline"
        LUGGAGE = "luggage", "Luggage tags"
        FORMULA = "formula", "Formula scrap"

    title = models.CharField(max_length=80)
    builds = models.CharField("what it lets me build", max_length=180, blank=True)
    seen_in = models.CharField(
        "seen in", max_length=120, blank=True, help_text="Projects that used these, comma separated."
    )
    icon = models.CharField(max_length=20, choices=Icon.choices, default=Icon.SPARK)
    style = models.CharField("visual style", max_length=20, choices=Style.choices, default=Style.STICKERS)

    class Meta(OrderedModel.Meta):
        verbose_name = "skill category"
        verbose_name_plural = "skill categories"

    def __str__(self):
        return self.title


class Skill(OrderedModel):
    category = models.ForeignKey(SkillCategory, on_delete=models.CASCADE, related_name="skills")
    name = models.CharField(max_length=80)
    is_minor = models.BooleanField(
        "coursework / minor", default=False, help_text="Shown muted, e.g. languages used only in coursework."
    )

    class Meta(OrderedModel.Meta):
        verbose_name = "skill"

    def __str__(self):
        return self.name


class Experience(OrderedModel):
    role = models.CharField(max_length=120)
    organization = models.CharField(max_length=120)
    location = models.CharField(max_length=120, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="Leave empty if this is your current role.")
    highlights = models.TextField(help_text="One achievement per line.")
    is_published = models.BooleanField("published", default=True)

    class Meta:
        ordering = ["order", "-start_date"]
        verbose_name = "work experience"
        verbose_name_plural = "work experience"

    def __str__(self):
        return f"{self.role} — {self.organization}"

    @property
    def highlight_list(self) -> list[str]:
        return [line.strip(" •-\t") for line in self.highlights.splitlines() if line.strip(" •-\t")]

    @property
    def is_current(self) -> bool:
        return self.end_date is None

    def clean(self):
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "The end date cannot be before the start date."})


class ExperienceLink(OrderedModel):
    experience = models.ForeignKey(Experience, on_delete=models.CASCADE, related_name="links")
    label = models.CharField(max_length=80)
    url = models.URLField()

    class Meta(OrderedModel.Meta):
        verbose_name = "link"

    def __str__(self):
        return self.label


class Education(OrderedModel):
    degree = models.CharField(max_length=80)
    field = models.CharField("field of study", max_length=120)
    institution = models.CharField(max_length=160)
    location = models.CharField(max_length=120, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="Leave empty while in progress.")
    score = models.CharField(max_length=60, blank=True, help_text="e.g. CGPA 8.8 / 10")
    focus = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ["order", "-start_date"]
        verbose_name = "education"
        verbose_name_plural = "education"

    def __str__(self):
        return f"{self.degree} — {self.field}"

    @property
    def in_progress(self) -> bool:
        return self.end_date is None


class Certification(OrderedModel):
    name = models.CharField(max_length=160)
    issuer = models.CharField(max_length=120)
    url = models.URLField("credential URL", blank=True)

    class Meta(OrderedModel.Meta):
        verbose_name = "certification"

    def __str__(self):
        return self.name


class Achievement(OrderedModel):
    title = models.CharField(max_length=120)
    detail = models.CharField(max_length=200, blank=True)

    class Meta(OrderedModel.Meta):
        verbose_name = "achievement"

    def __str__(self):
        return self.title


class Principle(OrderedModel):
    title = models.CharField(max_length=80)
    body = models.TextField(max_length=400)

    class Meta(OrderedModel.Meta):
        verbose_name = "working principle"

    def __str__(self):
        return self.title


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
class ProjectQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Project.Status.PUBLISHED, published_at__lte=timezone.now())

    def featured(self):
        return self.published().filter(is_featured=True)


class Project(OrderedModel, TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    class Art(models.TextChoices):
        GENERIC = "generic", "Generic notebook sketch"
        VASTRA = "vastra", "Retrieval / assistant flow"
        UNIFORM = "uniform", "Camera / computer vision"
        CINEMA = "cinema", "Film strip / recommender"
        FALCON = "falcon", "Rocket / data science"

    title = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, help_text="Used in the URL: /work/<slug>/")
    year = models.CharField(max_length=20, blank=True)
    tagline = models.CharField(max_length=200, blank=True, help_text="A one-line hook shown large on the card.")
    summary = models.TextField(max_length=600, help_text="Short description for cards and search results.")
    description = models.TextField(
        "full description",
        blank=True,
        help_text="Paragraphs separated by a blank line. Lines starting with '- ' become a bulleted list.",
    )
    contribution = models.TextField("my contribution", blank=True, help_text="One item per line.")
    outcomes = models.TextField(blank=True, help_text="Documented outcomes only, one per line.")
    technologies = models.CharField(max_length=300, blank=True, help_text="Comma separated, in display order.")
    note = models.CharField("margin note", max_length=80, blank=True, help_text="Handwritten annotation on the card.")

    featured_image = models.ImageField(
        upload_to=project_cover_path,
        blank=True,
        validators=IMAGE_VALIDATORS,
        width_field="featured_image_width",
        height_field="featured_image_height",
        help_text=IMAGE_HELP + " If empty, a hand-drawn sketch is shown instead.",
    )
    featured_image_width = models.PositiveIntegerField(null=True, blank=True, editable=False)
    featured_image_height = models.PositiveIntegerField(null=True, blank=True, editable=False)
    featured_image_alt = models.CharField(max_length=200, blank=True)
    art = models.CharField("fallback sketch", max_length=20, choices=Art.choices, default=Art.GENERIC)
    accent = models.CharField(max_length=7, default="#233F99", validators=[validate_hex_color])

    live_url = models.URLField("live demo URL", blank=True)
    github_url = models.URLField("source code URL", blank=True)
    extra_link_label = models.CharField(max_length=60, blank=True)
    extra_link_url = models.URLField(blank=True)

    is_featured = models.BooleanField("featured on homepage", default=False)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True)
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Set automatically when first published. A future date schedules the project.",
    )

    objects = ProjectQuerySet.as_manager()

    class Meta:
        ordering = ["order", "-published_at", "pk"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("portfolio:project_detail", kwargs={"slug": self.slug})

    @property
    def is_live(self) -> bool:
        return (
            self.status == self.Status.PUBLISHED
            and self.published_at is not None
            and self.published_at <= timezone.now()
        )

    @property
    def tech_list(self) -> list[str]:
        return [t.strip() for t in self.technologies.split(",") if t.strip()]

    @property
    def contribution_list(self) -> list[str]:
        return [line.strip(" •-\t") for line in self.contribution.splitlines() if line.strip(" •-\t")]

    @property
    def outcome_list(self) -> list[str]:
        return [line.strip(" •-\t") for line in self.outcomes.splitlines() if line.strip(" •-\t")]

    def clean(self):
        if self.featured_image and not self.featured_image_alt:
            raise ValidationError({"featured_image_alt": "Describe the featured image for screen-reader users."})
        if bool(self.extra_link_label) != bool(self.extra_link_url):
            raise ValidationError({"extra_link_url": "Provide both a label and a URL for the extra link, or neither."})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:140]
        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        optimise_image_field(self, "featured_image")
        super().save(*args, **kwargs)


class ProjectImage(OrderedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(
        upload_to=project_screenshot_path,
        validators=IMAGE_VALIDATORS,
        width_field="width",
        height_field="height",
        help_text=IMAGE_HELP,
    )
    width = models.PositiveIntegerField(null=True, blank=True, editable=False)
    height = models.PositiveIntegerField(null=True, blank=True, editable=False)
    alt_text = models.CharField(max_length=200, help_text="What the screenshot shows, for screen-reader users.")
    caption = models.CharField(max_length=160, blank=True)

    class Meta(OrderedModel.Meta):
        verbose_name = "screenshot"

    def __str__(self):
        return self.caption or self.alt_text

    def save(self, *args, **kwargs):
        optimise_image_field(self, "image")
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Private inbox
# ---------------------------------------------------------------------------
class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    message = models.TextField(max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    is_read = models.BooleanField("read", default=False)
    notified = models.BooleanField("email notification sent", default=False, editable=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "contact message"

    def __str__(self):
        return f"{self.name} <{self.email}>"
