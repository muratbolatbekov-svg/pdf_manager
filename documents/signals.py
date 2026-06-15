from django.contrib.auth.models import User
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from .models import AuditLog, Category, Document, DocumentVersion, UserProfile
from .utils import delete_cloudinary_file


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(pre_delete, sender=Document)
def delete_document_pdf(sender, instance, **kwargs):
    delete_cloudinary_file(instance.pdf_file)


@receiver(pre_delete, sender=DocumentVersion)
def delete_version_pdf(sender, instance, **kwargs):
    delete_cloudinary_file(instance.pdf_file)


def log_audit(user, action, instance, details=None):
    AuditLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        model_name=instance.__class__.__name__,
        object_id=instance.pk,
        object_repr=str(instance)[:255],
        details=details or {},
    )


@receiver(post_save, sender=Document)
def audit_document_save(sender, instance, created, **kwargs):
    user = getattr(instance, '_audit_user', None)
    action = AuditLog.ACTION_CREATE if created else AuditLog.ACTION_UPDATE
    log_audit(user, action, instance)


@receiver(post_delete, sender=Document)
def audit_document_delete(sender, instance, **kwargs):
    user = getattr(instance, '_audit_user', None)
    log_audit(user, AuditLog.ACTION_DELETE, instance)


@receiver(post_save, sender=Category)
def audit_category_save(sender, instance, created, **kwargs):
    user = getattr(instance, '_audit_user', None)
    action = AuditLog.ACTION_CREATE if created else AuditLog.ACTION_UPDATE
    log_audit(user, action, instance)


@receiver(post_delete, sender=Category)
def audit_category_delete(sender, instance, **kwargs):
    user = getattr(instance, '_audit_user', None)
    log_audit(user, AuditLog.ACTION_DELETE, instance)
