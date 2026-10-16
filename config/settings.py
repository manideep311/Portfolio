"""
Django settings for Manideep Chittimodu's portfolio.

Every environment-specific value comes from environment variables so the same
code runs locally (SQLite + local media) and in production (PostgreSQL +
S3-compatible object storage). See .env.example for the full list.
"""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    raw = env(name, default) or ""
    return [item.strip() for item in raw.split(",") if item.strip()]


def load_dotenv(path: Path) -> None:
    """Tiny .env loader for local development (no extra dependency)."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv(BASE_DIR / ".env")

# --------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------
DEBUG = env_bool("DJANGO_DEBUG", False)

SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-insecure-key-do-not-use-in-production"  # noqa: S105 (DEBUG only)
    else:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off.")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

# Public base URL used for canonical links, Open Graph and the sitemap.
SITE_URL = (env("SITE_URL", "") or "").rstrip("/")

# Admin lives at a configurable path; there is no public sign-up anywhere.
ADMIN_URL = (env("DJANGO_ADMIN_URL", "admin/") or "admin/").strip("/") + "/"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "storages",
    "portfolio",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # Compresses HTML responses; Django 4.2+ pads output to mitigate BREACH.
    "django.middleware.gzip.GZipMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "portfolio.middleware.ContentSecurityPolicyMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "portfolio.context_processors.site",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --------------------------------------------------------------------------
# Database — SQLite locally, PostgreSQL in production via DATABASE_URL
# --------------------------------------------------------------------------
# An empty DATABASE_URL (as in .env.example) means "use local SQLite".
DATABASE_URL = env("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=int(env("DATABASE_CONN_MAX_AGE", "60")),
        conn_health_checks=True,
        ssl_require=env_bool("DATABASE_SSL_REQUIRE", False),
    )
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --------------------------------------------------------------------------
# Internationalisation
# --------------------------------------------------------------------------
LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------------
# Static files (WhiteNoise) and media (local disk or S3-compatible storage)
# --------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = env("MEDIA_URL", "/media/")
MEDIA_ROOT = Path(env("MEDIA_ROOT", str(BASE_DIR / "media")))

AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
USE_S3_MEDIA = bool(AWS_STORAGE_BUCKET_NAME)

if USE_S3_MEDIA:
    # Works with AWS S3, Cloudflare R2, Backblaze B2, DigitalOcean Spaces…
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", "auto")
    AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN")
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = env_bool("AWS_QUERYSTRING_AUTH", False)
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "public, max-age=31536000, immutable"}
    AWS_LOCATION = env("AWS_LOCATION", "media")
    DEFAULT_STORAGE = {"BACKEND": "storages.backends.s3.S3Storage"}
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_LOCATION}/" if AWS_S3_CUSTOM_DOMAIN else MEDIA_URL
else:
    DEFAULT_STORAGE = {"BACKEND": "django.core.files.storage.FileSystemStorage"}

STORAGES = {
    "default": DEFAULT_STORAGE,
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

# Upload limits (validated per field in portfolio/validators.py)
MAX_IMAGE_UPLOAD_MB = int(env("MAX_IMAGE_UPLOAD_MB", "8"))
MAX_DOCUMENT_UPLOAD_MB = int(env("MAX_DOCUMENT_UPLOAD_MB", "10"))
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
# Uploaded images are re-encoded to WebP and capped to this long edge.
IMAGE_MAX_EDGE = int(env("IMAGE_MAX_EDGE", "2000"))

# --------------------------------------------------------------------------
# Email — contact form notifications (messages are always stored in the DB)
# --------------------------------------------------------------------------
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", "localhost")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "portfolio@localhost")
SERVER_EMAIL = DEFAULT_FROM_EMAIL
# Where new-message notifications go. Empty disables notifications.
CONTACT_NOTIFY_EMAIL = env("CONTACT_NOTIFY_EMAIL", "")

# Contact form rate limit: N submissions per window per client.
CONTACT_RATE_LIMIT = int(env("CONTACT_RATE_LIMIT", "5"))
CONTACT_RATE_WINDOW_SECONDS = int(env("CONTACT_RATE_WINDOW_SECONDS", "3600"))
# Only enable behind a proxy you trust (Render, Railway, Fly, Heroku all set it).
TRUST_X_FORWARDED_FOR = env_bool("TRUST_X_FORWARDED_FOR", False)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "portfolio",
    }
}

# --------------------------------------------------------------------------
# Security — strict by default in production, relaxed only with DEBUG
# --------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SECURE_REDIRECT_EXEMPT = [r"^healthz/$"]
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(env("DJANGO_SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
    SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)

# Extra origins allowed to serve images (e.g. your R2/S3 custom domain).
CSP_IMG_ORIGINS = env_list("CSP_IMG_ORIGINS")
if USE_S3_MEDIA:
    if AWS_S3_CUSTOM_DOMAIN:
        CSP_IMG_ORIGINS.append(f"https://{AWS_S3_CUSTOM_DOMAIN}")
    elif AWS_S3_ENDPOINT_URL:
        CSP_IMG_ORIGINS.append(AWS_S3_ENDPOINT_URL.rstrip("/"))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", "INFO")},
    "loggers": {"django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False}},
}

# Serve uploads through Django (only for a persistent-disk setup without object storage).
SERVE_MEDIA = env_bool("SERVE_MEDIA", False) and not USE_S3_MEDIA
