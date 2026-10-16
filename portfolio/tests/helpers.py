import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

from portfolio.models import Project, SiteProfile


def image_bytes(fmt="PNG", size=(320, 200), color=(35, 63, 153)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format=fmt)
    return buffer.getvalue()


def upload_image(name="shot.png", fmt="PNG", size=(320, 200)) -> SimpleUploadedFile:
    content_type = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp", "GIF": "image/gif"}[fmt]
    return SimpleUploadedFile(name, image_bytes(fmt, size), content_type=content_type)


def upload_pdf(name="resume.pdf") -> SimpleUploadedFile:
    return SimpleUploadedFile(
        name, b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n", content_type="application/pdf"
    )


def make_profile(**overrides) -> SiteProfile:
    data = {
        "name": "Manideep Chittimodu",
        "role": "Gen AI / ML Engineer",
        "focus": "NLP, LLMs & Applied ML",
        "headline": "I build ML systems end to end.",
        "intro": "Intro text.",
        "email": "me@example.com",
        "location": "Hyderabad, India",
        "availability": "Open to roles",
    }
    data.update(overrides)
    return SiteProfile.objects.create(**data)


def make_project(title="Vastra", status=Project.Status.PUBLISHED, featured=True, **overrides) -> Project:
    data = {
        "title": title,
        "summary": f"{title} summary.",
        "technologies": "Python, Django",
        "status": status,
        "is_featured": featured,
    }
    data.update(overrides)
    return Project.objects.create(**data)


class TempMediaMixin:
    """Each test class writes uploads into its own throwaway MEDIA_ROOT."""

    @classmethod
    def setUpClass(cls):
        cls._media_dir = tempfile.mkdtemp(prefix="portfolio-test-media-")
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_dir)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        shutil.rmtree(cls._media_dir, ignore_errors=True)
