"""Remove uploaded files from storage when their record is deleted or the file is replaced.

Deletion runs after the transaction commits, so a rolled-back save never
loses a file that is still referenced.
"""

from django.db import transaction
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from .models import Project, ProjectImage, SiteProfile

FILE_FIELDS = {
    Project: ["featured_image"],
    ProjectImage: ["image"],
    SiteProfile: ["portrait", "resume"],
}


def _delete_later(field_file):
    if not field_file or not field_file.name:
        return
    storage, name = field_file.storage, field_file.name
    transaction.on_commit(lambda: storage.delete(name))


def _on_delete(sender, instance, **kwargs):
    for field in FILE_FIELDS[sender]:
        _delete_later(getattr(instance, field))


def _on_replace(sender, instance, raw=False, **kwargs):
    if raw or not instance.pk:
        return
    try:
        previous = sender.objects.only(*FILE_FIELDS[sender]).get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    for field in FILE_FIELDS[sender]:
        old, new = getattr(previous, field), getattr(instance, field)
        if old and old.name != (new.name if new else None):
            _delete_later(old)


for model in FILE_FIELDS:
    receiver(post_delete, sender=model, dispatch_uid=f"cleanup-delete-{model.__name__}")(_on_delete)
    receiver(pre_save, sender=model, dispatch_uid=f"cleanup-replace-{model.__name__}")(_on_replace)
