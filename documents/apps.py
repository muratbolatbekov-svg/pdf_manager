from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DocumentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'documents'
    verbose_name = _('Документы')

    def ready(self):
        import documents.signals  # noqa: F401
        import documents.schema  # noqa: F401
