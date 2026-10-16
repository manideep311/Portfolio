from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image

from portfolio.models import Project, ProjectImage, SiteProfile

from .helpers import TempMediaMixin, make_profile, make_project, upload_image, upload_pdf


class ProjectModelTests(TempMediaMixin, TestCase):
    def test_slug_is_generated_from_title(self):
        project = make_project(title="Falcon 9 Landing Prediction")
        self.assertEqual(project.slug, "falcon-9-landing-prediction")
        self.assertEqual(project.get_absolute_url(), "/work/falcon-9-landing-prediction/")

    def test_publishing_sets_published_at_once(self):
        draft = make_project(status=Project.Status.DRAFT)
        self.assertIsNone(draft.published_at)
        draft.status = Project.Status.PUBLISHED
        draft.save()
        first = draft.published_at
        self.assertIsNotNone(first)
        draft.save()
        self.assertEqual(draft.published_at, first)

    def test_published_queryset_hides_drafts_and_scheduled(self):
        live = make_project(title="Live")
        make_project(title="Draft", status=Project.Status.DRAFT)
        make_project(title="Scheduled", published_at=timezone.now() + timedelta(days=3))
        self.assertQuerySetEqual(Project.objects.published(), [live])

    def test_featured_requires_published(self):
        featured = make_project(title="Featured")
        make_project(title="Not featured", featured=False)
        make_project(title="Featured draft", status=Project.Status.DRAFT)
        self.assertQuerySetEqual(Project.objects.featured(), [featured])

    def test_display_order(self):
        second = make_project(title="Second", order=2)
        first = make_project(title="First", order=1)
        self.assertEqual(list(Project.objects.published()), [first, second])

    def test_list_helpers(self):
        project = make_project(
            technologies=" Python ,  OpenCV,,DeepFace ", contribution="- one\n\n• two\nthree", outcomes="Live\n"
        )
        self.assertEqual(project.tech_list, ["Python", "OpenCV", "DeepFace"])
        self.assertEqual(project.contribution_list, ["one", "two", "three"])
        self.assertEqual(project.outcome_list, ["Live"])

    def test_featured_image_needs_alt_text(self):
        project = Project(title="X", slug="x", summary="s", featured_image=upload_image("cover.png"))
        with self.assertRaises(ValidationError) as ctx:
            project.full_clean()
        self.assertIn("featured_image_alt", ctx.exception.message_dict)

    def test_accent_must_be_hex(self):
        project = Project(title="X", slug="x", summary="s", accent="red")
        with self.assertRaises(ValidationError) as ctx:
            project.full_clean()
        self.assertIn("accent", ctx.exception.message_dict)


class SiteProfileTests(TempMediaMixin, TestCase):
    def test_only_one_profile_can_be_created(self):
        make_profile()
        second = SiteProfile(name="Other", role="r", headline="h", intro="i", email="o@example.com")
        with self.assertRaises(ValidationError):
            second.full_clean()

    def test_name_helpers(self):
        profile = make_profile()
        self.assertEqual(profile.first_name, "Manideep")
        self.assertEqual(profile.last_name, "Chittimodu")
        self.assertEqual(profile.initials, "MC")

    def test_about_paragraphs(self):
        profile = make_profile(about="One.\n\nTwo.\n\n\n")
        self.assertEqual(profile.about_paragraphs, ["One.", "Two."])

    def test_resume_accepts_pdf(self):
        profile = make_profile()
        profile.resume = upload_pdf()
        profile.full_clean()
        profile.save()
        self.assertTrue(profile.resume.name.endswith(".pdf"))


class ImageOptimisationTests(TempMediaMixin, TestCase):
    @override_settings(IMAGE_MAX_EDGE=800)
    def test_screenshots_are_reencoded_to_webp_and_resized(self):
        project = make_project()
        shot = ProjectImage(project=project, image=upload_image("big.png", size=(2400, 1200)), alt_text="Dashboard")
        shot.full_clean()
        shot.save()
        shot.refresh_from_db()
        self.assertTrue(shot.image.name.endswith(".webp"))
        self.assertIn(f"projects/{project.slug}/screenshots/", shot.image.name)
        self.assertEqual((shot.width, shot.height), (800, 400))
        with Image.open(shot.image.path) as img:
            self.assertEqual(img.format, "WEBP")
            self.assertEqual(img.size, (800, 400))

    def test_editing_other_fields_keeps_the_stored_file(self):
        project = make_project()
        shot = ProjectImage.objects.create(project=project, image=upload_image(), alt_text="A")
        original = shot.image.name
        shot.caption = "New caption"
        shot.full_clean()
        shot.save()
        shot.refresh_from_db()
        self.assertEqual(shot.image.name, original)

    def test_files_are_removed_when_deleted_or_replaced(self):
        import os

        project = make_project()
        shot = ProjectImage.objects.create(project=project, image=upload_image(), alt_text="A")
        first_path = shot.image.path
        with self.captureOnCommitCallbacks(execute=True):
            shot.image = upload_image("replacement.png")
            shot.save()
        self.assertFalse(os.path.exists(first_path))
        second_path = shot.image.path
        self.assertTrue(os.path.exists(second_path))
        with self.captureOnCommitCallbacks(execute=True):
            project.delete()
        self.assertFalse(os.path.exists(second_path))

    def test_uploaded_names_are_random(self):
        project = make_project()
        a = ProjectImage.objects.create(project=project, image=upload_image("same.png"), alt_text="A")
        b = ProjectImage.objects.create(project=project, image=upload_image("same.png"), alt_text="B")
        self.assertNotEqual(a.image.name, b.image.name)
        self.assertNotIn("same", a.image.name)


class PortraitFilmLookTests(TempMediaMixin, TestCase):
    def _mean_rgb(self, path):
        with Image.open(path) as img:
            small = img.convert("RGB").resize((1, 1), Image.Resampling.BOX)
            return small.getpixel((0, 0))

    def test_portrait_gets_the_film_look_by_default(self):
        profile = make_profile()
        profile.portrait = upload_image("me.png", size=(900, 900))  # solid notebook blue
        profile.portrait_alt = "Me"
        profile.full_clean()
        profile.save()
        profile.refresh_from_db()
        self.assertTrue(profile.portrait.name.endswith(".webp"))
        r, g, b = self._mean_rgb(profile.portrait.path)
        # Lifted blacks and warm split tone move the flat blue towards paper and ink
        self.assertGreater(r, 35)
        self.assertLess(b, 153)
        self.assertEqual((profile.portrait_width, profile.portrait_height), (900, 900))

    def test_film_look_can_be_switched_off(self):
        profile = make_profile(portrait_film_look=False)
        profile.portrait = upload_image("me.png", size=(400, 400))
        profile.portrait_alt = "Me"
        profile.save()
        r, g, b = self._mean_rgb(profile.portrait.path)
        self.assertAlmostEqual(r, 35, delta=4)
        self.assertAlmostEqual(b, 153, delta=4)

    def test_portrait_requires_alt_text(self):
        profile = make_profile()
        profile.portrait = upload_image("me.png")
        with self.assertRaises(ValidationError) as ctx:
            profile.full_clean()
        self.assertIn("portrait_alt", ctx.exception.message_dict)


class ProjectImageValidationTests(TempMediaMixin, TestCase):
    def setUp(self):
        self.project = make_project()

    def clean(self, upload):
        shot = ProjectImage(project=self.project, image=upload, alt_text="Alt")
        shot.full_clean()

    def test_accepts_png_jpeg_webp(self):
        for name, fmt in [("a.png", "PNG"), ("b.jpg", "JPEG"), ("c.webp", "WEBP")]:
            with self.subTest(fmt=fmt):
                self.clean(upload_image(name, fmt))

    def test_rejects_text_disguised_as_png(self):
        fake = SimpleUploadedFile("evil.png", b"<?php echo 'hi'; ?>", content_type="image/png")
        with self.assertRaises(ValidationError):
            self.clean(fake)

    def test_rejects_svg(self):
        svg = SimpleUploadedFile(
            "logo.svg",
            b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>",
            content_type="image/svg+xml",
        )
        with self.assertRaises(ValidationError):
            self.clean(svg)

    def test_rejects_gif_even_with_allowed_extension(self):
        gif = upload_image("anim.png", "GIF")
        with self.assertRaises(ValidationError) as ctx:
            self.clean(gif)
        self.assertIn("not allowed", str(ctx.exception))

    @override_settings(MAX_IMAGE_UPLOAD_MB=0)
    def test_rejects_oversized_files(self):
        with self.assertRaises(ValidationError) as ctx:
            self.clean(upload_image())
        self.assertIn("maximum allowed size", str(ctx.exception))

    def test_alt_text_is_required(self):
        shot = ProjectImage(project=self.project, image=upload_image(), alt_text="")
        with self.assertRaises(ValidationError) as ctx:
            shot.full_clean()
        self.assertIn("alt_text", ctx.exception.message_dict)


class ResumeValidationTests(TempMediaMixin, TestCase):
    def test_rejects_non_pdf(self):
        profile = make_profile()
        profile.resume = SimpleUploadedFile("resume.pdf", b"MZ\x90\x00 not a pdf", content_type="application/pdf")
        with self.assertRaises(ValidationError) as ctx:
            profile.full_clean()
        self.assertIn("resume", ctx.exception.message_dict)

    def test_rejects_wrong_extension(self):
        profile = make_profile()
        profile.resume = SimpleUploadedFile("resume.docx", b"%PDF-1.4 sneaky", content_type="application/pdf")
        with self.assertRaises(ValidationError):
            profile.full_clean()

    @override_settings(MAX_DOCUMENT_UPLOAD_MB=0)
    def test_rejects_oversized_pdf(self):
        profile = make_profile()
        profile.resume = upload_pdf()
        with self.assertRaises(ValidationError):
            profile.full_clean()
