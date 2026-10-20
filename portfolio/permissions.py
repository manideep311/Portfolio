"""Default staff roles, built on Django's permission system.

* Portfolio editors — manage every piece of public content, but cannot read
  private contact messages.
* Inbox readers — can read contact messages and mark them handled.

Superusers can do everything. Assign roles under Authentication → Users.
"""

from django.contrib.auth.models import Group, Permission

CONTENT_MODELS = [
    "siteprofile",
    "sociallink",
    "skillcategory",
    "skill",
    "experience",
    "experiencelink",
    "education",
    "certification",
    "achievement",
    "principle",
    "project",
    "projectimage",
]

EDITORS = "Portfolio editors"
INBOX = "Inbox readers"


def ensure_default_groups(sender=None, **kwargs):
    editors, _ = Group.objects.get_or_create(name=EDITORS)
    content_perms = Permission.objects.filter(
        content_type__app_label="portfolio", content_type__model__in=CONTENT_MODELS
    )
    editors.permissions.add(*content_perms)

    inbox, _ = Group.objects.get_or_create(name=INBOX)
    inbox_perms = Permission.objects.filter(
        content_type__app_label="portfolio",
        content_type__model="contactmessage",
        codename__in=["view_contactmessage", "change_contactmessage", "delete_contactmessage"],
    )
    inbox.permissions.add(*inbox_perms)
