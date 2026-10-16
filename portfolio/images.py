"""Image optimisation for uploads: fix orientation, cap size, re-encode as WebP."""

from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

WEBP_QUALITY = 82


def is_new_upload(field_file) -> bool:
    return bool(field_file) and getattr(field_file, "_committed", True) is False


def optimise_image_field(instance, field_name: str, max_edge: int | None = None, transform=None) -> None:
    """Replace a freshly uploaded image with an optimised WebP version.

    Called from model.save() before the row is written. Files that are
    already stored are left untouched, so editing other fields is cheap.
    ``transform`` optionally restyles the image (e.g. the portrait film look).
    """
    field_file = getattr(instance, field_name)
    if not is_new_upload(field_file):
        return

    max_edge = max_edge or settings.IMAGE_MAX_EDGE
    field_file.seek(0)
    with Image.open(field_file) as source:
        image = ImageOps.exif_transpose(source)
        if image.mode in ("P", "LA"):
            image = image.convert("RGBA")
        elif image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGB")
        image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
        if transform is not None:
            image = transform(image)

        buffer = BytesIO()
        image.save(buffer, format="WEBP", quality=WEBP_QUALITY, method=6)

    stem = Path(field_file.name).stem or "image"
    field_file.save(f"{stem}.webp", ContentFile(buffer.getvalue()), save=False)
