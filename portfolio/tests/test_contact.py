from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from portfolio.models import ContactMessage

from .helpers import make_profile

VALID = {"name": "Ada", "email": "ada@example.com", "message": "Hello there, I'd like to talk about a role."}


class ContactFormTests(TestCase):
    def setUp(self):
        cache.clear()
        make_profile()
        self.url = reverse("portfolio:contact")

    def test_valid_message_is_stored_privately(self):
        response = self.client.post(self.url, VALID)
        self.assertRedirects(response, reverse("portfolio:contact_thanks"))
        message = ContactMessage.objects.get()
        self.assertEqual(message.email, "ada@example.com")
        self.assertFalse(message.is_read)
        # Never shown on public pages
        self.assertNotContains(self.client.get("/"), "ada@example.com")

    def test_invalid_message_shows_errors(self):
        response = self.client.post(self.url, {"name": "", "email": "nope", "message": "short"})
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Enter a valid email address", status_code=400)
        self.assertContains(response, "at least a sentence", status_code=400)
        self.assertFalse(ContactMessage.objects.exists())

    def test_honeypot_silently_drops_bots(self):
        response = self.client.post(self.url, {**VALID, "website": "http://spam.example"})
        self.assertRedirects(response, reverse("portfolio:contact_thanks"))
        self.assertFalse(ContactMessage.objects.exists())

    def test_csrf_is_enforced(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(self.url, VALID)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ContactMessage.objects.exists())

    def test_csrf_token_flow_works(self):
        client = Client(enforce_csrf_checks=True)
        page = client.get(self.url)
        token = page.cookies["csrftoken"].value
        response = client.post(self.url, {**VALID, "csrfmiddlewaretoken": token})
        self.assertEqual(response.status_code, 302)

    @override_settings(CONTACT_RATE_LIMIT=3)
    def test_rate_limit(self):
        for _ in range(3):
            self.assertEqual(self.client.post(self.url, VALID).status_code, 302)
        response = self.client.post(self.url, VALID)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(ContactMessage.objects.count(), 3)

    @override_settings(
        CONTACT_NOTIFY_EMAIL="owner@example.com", EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
    )
    def test_notification_email(self):
        self.client.post(self.url, VALID)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Ada", mail.outbox[0].subject)
        self.assertTrue(ContactMessage.objects.get().notified)

    @override_settings(
        CONTACT_NOTIFY_EMAIL="owner@example.com", EMAIL_BACKEND="portfolio.tests.test_contact.BrokenBackend"
    )
    def test_message_saved_even_if_email_fails(self):
        with self.assertLogs("portfolio.views", level="ERROR"):
            response = self.client.post(self.url, VALID)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ContactMessage.objects.get().notified)

    def test_get_only_and_post(self):
        self.assertEqual(self.client.put(self.url).status_code, 405)


class BrokenBackend:
    def __init__(self, *args, **kwargs):
        pass

    def send_messages(self, messages):
        raise ConnectionError("SMTP down")
