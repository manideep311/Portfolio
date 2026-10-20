from datetime import timedelta

from django.contrib.auth.models import Permission, User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from portfolio.models import Project, ProjectImage

from .helpers import TempMediaMixin, make_profile, make_project, upload_image


class HomePageTests(TempMediaMixin, TestCase):
    def setUp(self):
        make_profile()

    def test_home_renders_profile(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manideep")
        self.assertContains(response, 'href="mailto:me@example.com"')
        self.assertContains(response, '<html lang="en-IN"')

    def test_work_page_lists_published_projects_featured_first(self):
        make_project(title="Plain Published", featured=False, order=0)
        make_project(title="Live Featured", order=5)
        make_project(title="Secret Draft", status=Project.Status.DRAFT)
        make_project(title="Future Launch", published_at=timezone.now() + timedelta(days=1))
        body = self.client.get("/work/").content.decode()
        self.assertLess(body.index("Live Featured"), body.index("Plain Published"))
        self.assertNotIn("Secret Draft", body)
        self.assertNotIn("Future Launch", body)

    def test_home_without_profile_does_not_crash(self):
        from portfolio.models import SiteProfile

        SiteProfile.objects.all().delete()
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "seed_portfolio")

    def test_phone_hidden_unless_enabled(self):
        from portfolio.models import SiteProfile

        SiteProfile.objects.update(phone="+91-0000000000", show_phone=False)
        self.assertNotContains(self.client.get("/contact/"), "+91-0000000000")
        SiteProfile.objects.update(show_phone=True)
        self.assertContains(self.client.get("/contact/"), "+91-0000000000")

    def test_security_headers_on_public_pages(self):
        response = self.client.get("/")
        csp = response["Content-Security-Policy"]
        self.assertIn("default-src 'self'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertRegex(csp, r"script-src 'self' 'nonce-[\w-]+'")
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        # The inline bootstrap script carries the same nonce
        nonce = csp.split("'nonce-")[1].split("'")[0]
        self.assertContains(response, f'nonce="{nonce}"')


class ProjectPageTests(TempMediaMixin, TestCase):
    def setUp(self):
        make_profile()

    def test_published_project_detail_with_screenshots(self):
        project = make_project(title="Vastra", description="Para one.\n\n- bullet a\n- bullet b")
        ProjectImage.objects.create(
            project=project, image=upload_image(), alt_text="Assistant answering a buyer", caption="Chat view", order=2
        )
        ProjectImage.objects.create(project=project, image=upload_image(), alt_text="Supplier dashboard", order=1)
        response = self.client.get(project.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'alt="Assistant answering a buyer"')
        self.assertContains(response, "Chat view")
        self.assertContains(response, '<ul class="bullets" role="list"><li>bullet a</li>')
        body = response.content.decode()
        self.assertLess(body.index("Supplier dashboard"), body.index("Assistant answering a buyer"))

    def test_description_html_is_escaped(self):
        project = make_project(description="<script>alert('x')</script>")
        response = self.client.get(project.get_absolute_url())
        self.assertNotContains(response, "<script>alert('x')</script>")
        self.assertContains(response, "&lt;script&gt;")

    def test_draft_is_404_for_visitors(self):
        draft = make_project(title="Draft", status=Project.Status.DRAFT)
        self.assertEqual(self.client.get(draft.get_absolute_url()).status_code, 404)

    def test_scheduled_is_404_for_visitors(self):
        scheduled = make_project(title="Soon", published_at=timezone.now() + timedelta(hours=2))
        self.assertEqual(self.client.get(scheduled.get_absolute_url()).status_code, 404)

    def test_staff_with_permission_can_preview_drafts(self):
        draft = make_project(title="Draft", status=Project.Status.DRAFT)
        editor = User.objects.create_user("editor", password="x-long-password-1", is_staff=True)
        editor.user_permissions.add(Permission.objects.get(codename="view_project"))
        self.client.force_login(editor)
        response = self.client.get(draft.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Draft preview")
        self.assertContains(response, '<meta name="robots" content="noindex, nofollow">')
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")

    def test_staff_without_permission_cannot_preview(self):
        draft = make_project(title="Draft", status=Project.Status.DRAFT)
        staff = User.objects.create_user("staff", password="x-long-password-1", is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(draft.get_absolute_url()).status_code, 404)

    def test_regular_user_cannot_preview(self):
        draft = make_project(title="Draft", status=Project.Status.DRAFT)
        user = User.objects.create_user("visitor", password="x-long-password-1")
        self.client.force_login(user)
        self.assertEqual(self.client.get(draft.get_absolute_url()).status_code, 404)

    def test_project_index_lists_published_only(self):
        make_project(title="Shown Project", featured=False)
        make_project(title="Hidden Project", status=Project.Status.DRAFT)
        response = self.client.get(reverse("portfolio:project_list"))
        self.assertContains(response, "Shown Project")
        self.assertNotContains(response, "Hidden Project")


class DiscoveryTests(TestCase):
    def setUp(self):
        make_profile()

    def test_sitemap_lists_only_published_projects(self):
        make_project(title="Public One")
        make_project(title="Private One", status=Project.Status.DRAFT)
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/work/public-one/")
        self.assertNotContains(response, "/work/private-one/")

    @override_settings(SITE_URL="")
    def test_robots_points_to_sitemap(self):
        response = self.client.get("/robots.txt")
        self.assertContains(response, "Sitemap: http://testserver/sitemap.xml")

    @override_settings(SITE_URL="https://manideep.example")
    def test_site_url_drives_canonical_and_sitemap_links(self):
        self.assertContains(self.client.get("/robots.txt"), "Sitemap: https://manideep.example/sitemap.xml")
        home = self.client.get("/")
        self.assertContains(home, '<link rel="canonical" href="https://manideep.example/">')
        self.assertContains(home, 'property="og:image" content="https://manideep.example/static/img/og-image')

    def test_healthz(self):
        self.assertContains(self.client.get("/healthz/"), "ok")

    def test_custom_404(self):
        response = self.client.get("/definitely-not-here/")
        self.assertEqual(response.status_code, 404)

    def test_there_is_no_public_registration(self):
        for path in ["/accounts/signup/", "/register/", "/signup/", "/accounts/register/"]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_no_playground_bot_or_field_notes(self):
        self.assertEqual(self.client.get("/playground/").status_code, 404)
        response = self.client.get("/")
        self.assertNotContains(response, "notebook-notes")
        self.assertNotContains(response, "data-bot")
        self.assertNotContains(response, "Field notes")
        self.assertNotContains(response, "hero-shot")

    def test_work_loop_sits_on_the_about_page(self):
        body = self.client.get("/about/").content.decode()
        self.assertIn('class="loop-note about__loop', body)
        self.assertIn("how I like to work", body)
