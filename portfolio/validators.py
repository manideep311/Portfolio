"""Upload validators: file type is checked by content, not just by extension."""

import contextlib

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from PIL import Image, UnidentifiedImageError

ALLOWED_IMAGE_FORMATS = {"JPEG": "JPEG", "PNG": "PNG", "WEBP": "WebP"}
ALLOWED_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]
MAX_IMAGE_PIXELS = 40_000_000  # ~ 8000 x 5000; guards against decompression bombs


def _already_stored(file) -> bool:
    """Files already saved to storage were validated when they were uploaded."""
    return getattr(file, "_committed", False) is True


def _megabytes(num_bytes: int) -> str:
    return f"{num_bytes / (1024 * 1024):.1f} MB"


@deconstructible
class MaxFileSizeValidator:
    def __init__(self, setting_name: str):
        self.setting_name = setting_name

    @property
    def limit_bytes(self) -> int:
        return getattr(settings, self.setting_name) * 1024 * 1024

    def __call__(self, file):
        if _already_stored(file):
            return
        size = getattr(file, "size", None)
        if size is not None and size > self.limit_bytes:
            raise ValidationError(
                "This file is %(size)s. The maximum allowed size is %(limit)s.",
                code="file_too_large",
                params={"size": _megabytes(size), "limit": _megabytes(self.limit_bytes)},
            )

    def __eq__(self, other):
        return isinstance(other, MaxFileSizeValidator) and other.setting_name == self.setting_name


validate_image_size = MaxFileSizeValidator("MAX_IMAGE_UPLOAD_MB")
validate_document_size = MaxFileSizeValidator("MAX_DOCUMENT_UPLOAD_MB")


def validate_image_content(file):
    """Accept only real JPEG, PNG or WebP images (SVG and others are rejected)."""
    if _already_stored(file):
        return
    try:
        position = file.tell() if hasattr(file, "tell") else None
        file.seek(0)
        with Image.open(file) as image:
            image_format = image.format
            width, height = image.size
            image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise ValidationError("Upload a valid JPEG, PNG or WebP image.", code="invalid_image") from exc
    finally:
        with contextlib.suppress(Exception):
            file.seek(position or 0)

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError(
            "%(format)s images are not allowed. Use JPEG, PNG or WebP.",
            code="invalid_image_format",
            params={"format": image_format or "This"},
        )
    if width * height > MAX_IMAGE_PIXELS:
        raise ValidationError(
            "This image is too large (%(w)s×%(h)s px).", code="image_too_many_pixels", params={"w": width, "h": height}
        )


def validate_pdf(file):
    """Accept only genuine PDF documents (checks the %PDF- signature)."""
    if _already_stored(file):
        return
    try:
        position = file.tell() if hasattr(file, "tell") else 0
        file.seek(0)
        header = file.read(5)
        file.seek(position or 0)
    except Exception as exc:  # pragma: no cover - defensive
        raise ValidationError("Could not read the uploaded file.", code="unreadable") from exc
    if isinstance(header, str):
        header = header.encode()
    if header != b"%PDF-":
        raise ValidationError("Upload a PDF document.", code="invalid_pdf")


def validate_hex_color(value: str):
    import re

    if not re.fullmatch(r"#[0-9a-fA-F]{6}", value or ""):
        raise ValidationError("Use a hex colour like #B5462E.", code="invalid_color")
