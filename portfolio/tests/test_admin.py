from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from portfolio.models import ContactMessage, Project, SiteProfile
from portfolio.permissions import EDITORS, INBOX

from .helpers import TempMediaMixin, make_profile, make_project, upload_image

PASSWORD = "a-very-long-test-password-42"


def project_form(**overrides):
    """POST data for the admin 'add project' form with its screenshot inline."""
    data = {
        "title": "Notebook RAG",
        "slug": "notebook-rag",
        "year": "2026",
        "tagline": "Answers from my notes.",
        "summary": "A retrieval demo built for the portfolio.",
        "description": "First paragraph.\n\n- Retrieval\n- Generation",
        "contribution": "Built everything",
        "outcomes": "Works",
        "technologies": "Python, Django",
        "note": "hello",
        "featured_image_alt": "",
        "art": "generic",
        "accent": "#233F99",
        "live_url": "",
        "github_url": "https://github.com/example/notebook-rag",
        "extra_link_label": "",
        "extra_link_url": "",
        "status": "draft",
        "order": "0",
        "published_at_0": "",
        "published_at_1": "",
        "images-TOTAL_FORMS": "0",
        "images-INITIAL_FORMS": "0",
        "images-MIN_NUM_FORMS": "0",
        "images-MAX_NUM_FORMS": "1000",
        "_save": "Save",
    }
    data.update(overrides)
    return data


class AdminAccessTests(TestCase):
    def setUp(self):
        call_command("migrate", verbosity=0)  # makes sure default groups exist

    def test_admin_requires_login(self):
        response = self.client.get(reverse("admin:index"))
        self.assertRedirects(response, f"{reverse('admin:login')}?next={reverse('admin:index')}")

    def test_login_page_is_branded_and_noindexed(self):
        response = self.client.get(reverse("admin:login"))
        self.assertContains(response, "Manideep&#x27;s Notebook")
        self.assertContains(response, "notebook-admin")
        self.assertContains(response, 'content="noindex, nofollow"')

    def test_non_staff_user_cannot_use_admin(self):
        User.objects.create_user("visitor", password=PASSWORD)
        self.assertTrue(self.client.login(username="visitor", password=PASSWORD))
        response = self.client.get(reverse("admin:portfolio_project_changelist"))
        self.assertEqual(response.status_code, 302)

    def test_default_groups_exist(self):
        editors = Group.objects.get(name=EDITORS)
        inbox = Group.objects.get(name=INBOX)
        self.assertTrue(editors.permissions.filter(codename="change_project").exists())
        self.assertFalse(editors.permissions.filter(codename__contains="contactmessage").exists())
        self.assertTrue(inbox.permissions.filter(codename="view_contactmessage").exists())
        self.assertFalse(inbox.permissions.filter(codename="add_contactmessage").exists())

    def test_editors_cannot_read_private_messages(self):
        ContactMessage.objects.create(name="Secret", email="s@example.com", message="Private note here.")
        editor = User.objects.create_user("editor", password=PASSWORD, is_staff=True)
        editor.groups.add(Group.objects.get(name=EDITORS))
        self.client.force_login(editor)
        self.assertEqual(self.client.get(reverse("admin:portfolio_project_changelist")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:portfolio_contactmessage_changelist")).status_code, 403)
        index = self.client.get(reverse("admin:index"))
        self.assertNotContains(index, "Contact messages")

    def test_inbox_readers_can_read_messages_and_marks_them_read(self):
        message = ContactMessage.objects.create(name="Ada", email="ada@example.com", message="Hello there friend.")
        reader = User.objects.create_user("reader", password=PASSWORD, is_staff=True)
        reader.groups.add(Group.objects.get(name=INBOX))
        self.client.force_login(reader)
        self.assertContains(self.client.get(reverse("admin:portfolio_contactmessage_changelist")), "ada@example.com")
        self.client.get(reverse("admin:portfolio_contactmessage_change", args=[message.pk]))
        message.refresh_from_db()
        self.assertTrue(message.is_read)
        # cannot edit projects
        self.assertEqual(self.client.get(reverse("admin:portfolio_project_changelist")).status_code, 403)

    def test_messages_cannot_be_created_from_admin(self):
        admin = User.objects.create_superuser("root", "root@example.com", PASSWORD)
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse("admin:portfolio_contactmessage_add")).status_code, 403)


class ProfileSingletonAdminTests(TempMediaMixin, TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("root", "root@example.com", PASSWORD)
        self.client.force_login(self.admin)

    def test_changelist_redirects_to_the_single_profile(self):
        profile = make_profile()
        response = self.client.get(reverse("admin:portfolio_siteprofile_changelist"))
        self.assertRedirects(response, reverse("admin:portfolio_siteprofile_change", args=[profile.pk]))

    def test_cannot_add_second_profile_or_delete(self):
        profile = make_profile()
        self.assertEqual(self.client.get(reverse("admin:portfolio_siteprofile_add")).status_code, 403)
        self.assertEqual(
            self.client.get(reverse("admin:portfolio_siteprofile_delete", args=[profile.pk])).status_code, 403
        )


class ProjectWorkflowTests(TempMediaMixin, TestCase):
    """The complete CMS journey: sign in → create → upload screenshots → publish → public."""

    def setUp(self):
        make_profile()
        self.admin = User.objects.create_superuser("manideep", "me@example.com", PASSWORD)

    def test_sign_in_create_upload_publish_and_view(self):
        # 1. Sign in through the real login form
        response = self.client.post(
            reverse("admin:login"),
            {"username": "manideep", "password": PASSWORD, "next": reverse("admin:index")},
        )
        self.assertRedirects(response, reverse("admin:index"))

        # 2. Create a draft project with two screenshots in one save
        data = project_form(
            **{
                "images-TOTAL_FORMS": "2",
                "images-0-image": upload_image("chat.png"),
                "images-0-alt_text": "Chat answering a question",
                "images-0-caption": "The assistant",
                "images-0-order": "2",
                "images-1-image": upload_image("index.jpg", "JPEG"),
                "images-1-alt_text": "Search index view",
                "images-1-caption": "",
                "images-1-order": "1",
            }
        )
        response = self.client.post(reverse("admin:portfolio_project_add"), data)
        self.assertRedirects(response, reverse("admin:portfolio_project_changelist"))
        project = Project.objects.get(slug="notebook-rag")
        self.assertEqual(project.status, Project.Status.DRAFT)
        self.assertEqual(project.images.count(), 2)
        self.assertTrue(all(img.image.name.endswith(".webp") for img in project.images.all()))

        # 3. Draft is invisible to the public
        visitor = self.client_class()
        self.assertEqual(visitor.get("/work/notebook-rag/").status_code, 404)
        self.assertNotContains(visitor.get("/work/"), "Notebook RAG")

        # 4. Publish and feature it with the changelist action
        response = self.client.post(
            reverse("admin:portfolio_project_changelist"),
            {"action": "publish", "_selected_action": [project.pk]},
            follow=True,
        )
        self.assertContains(response, "Published 1 project")
        self.client.post(
            reverse("admin:portfolio_project_changelist"), {"action": "feature", "_selected_action": [project.pk]}
        )
        project.refresh_from_db()
        self.assertTrue(project.is_live)
        self.assertTrue(project.is_featured)

        # 5. Now it is public: detail page, project index and homepage gallery
        detail = visitor.get("/work/notebook-rag/")
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Notebook RAG")
        self.assertContains(detail, 'alt="Chat answering a question"')
        self.assertContains(detail, 'alt="Search index view"')
        self.assertContains(detail, 'href="https://github.com/example/notebook-rag"')
        self.assertContains(visitor.get("/work/"), "Notebook RAG")
        self.assertContains(visitor.get("/"), "/work/notebook-rag/")

    def test_add_more_screenshots_to_existing_project(self):
        self.client.force_login(self.admin)
        project = make_project(title="Existing", slug="existing")
        first = project.images.create(image=upload_image(), alt_text="First", order=0)
        url = reverse("admin:portfolio_project_change", args=[project.pk])
        data = project_form(
            title="Existing",
            slug="existing",
            status="published",
            published_at_0=project.published_at.strftime("%Y-%m-%d"),
            published_at_1=project.published_at.strftime("%H:%M:%S"),
            **{
                "images-TOTAL_FORMS": "2",
                "images-INITIAL_FORMS": "1",
                "images-0-id": str(first.pk),
                "images-0-project": str(project.pk),
                "images-0-alt_text": "First, renamed",
                "images-0-caption": "",
                "images-0-order": "0",
                "images-1-project": str(project.pk),
                "images-1-image": upload_image("second.webp", "WEBP"),
                "images-1-alt_text": "Second",
                "images-1-caption": "",
                "images-1-order": "1",
            },
        )
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302, getattr(response, "context", None) and response.context["errors"])
        self.assertEqual(project.images.count(), 2)
        self.assertTrue(project.images.filter(alt_text="First, renamed").exists())

    def test_admin_rejects_bad_upload_with_a_clear_error(self):
        self.client.force_login(self.admin)
        from django.core.files.uploadedfile import SimpleUploadedFile

        data = project_form(
            **{
                "images-TOTAL_FORMS": "1",
                "images-0-image": SimpleUploadedFile("evil.png", b"not an image", content_type="image/png"),
                "images-0-alt_text": "Bad",
                "images-0-order": "0",
            }
        )
        response = self.client.post(reverse("admin:portfolio_project_add"), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upload a valid image")
        self.assertFalse(Project.objects.exists())

    def test_changelist_search_and_filters(self):
        self.client.force_login(self.admin)
        make_project(title="Vastra", technologies="Hugging Face")
        make_project(title="NextCinema", status=Project.Status.DRAFT, technologies="Next.js")
        url = reverse("admin:portfolio_project_changelist")
        self.assertContains(self.client.get(url, {"q": "hugging"}), "Vastra")
        self.assertNotContains(self.client.get(url, {"q": "hugging"}), "NextCinema")
        drafts = self.client.get(url, {"status__exact": "draft"})
        self.assertContains(drafts, "NextCinema")
        self.assertNotContains(drafts, ">Vastra<")

    def test_unpublish_hides_project(self):
        self.client.force_login(self.admin)
        project = make_project(title="Temporary")
        self.client.post(
            reverse("admin:portfolio_project_changelist"), {"action": "unpublish", "_selected_action": [project.pk]}
        )
        self.assertEqual(self.client_class().get(project.get_absolute_url()).status_code, 404)


class SeedCommandTests(TempMediaMixin, TestCase):
    def test_seed_is_idempotent_and_keeps_messages(self):
        ContactMessage.objects.create(name="Keep", email="k@example.com", message="Please keep me around.")
        call_command("seed_portfolio", verbosity=0)
        self.assertEqual(SiteProfile.objects.count(), 1)
        self.assertEqual(Project.objects.featured().count(), 4)
        self.assertTrue(SiteProfile.load().resume.name.endswith(".pdf"))
        portrait = SiteProfile.load().portrait
        self.assertTrue(portrait.name.endswith(".webp"))
        self.assertTrue(SiteProfile.load().portrait_alt)
        call_command("seed_portfolio", verbosity=0)
        self.assertEqual(Project.objects.count(), 4)
        call_command("seed_portfolio", "--reset", verbosity=0)
        self.assertEqual(Project.objects.count(), 4)
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertEqual(self.client.get("/").status_code, 200)
