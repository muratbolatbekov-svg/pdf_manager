from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'documents'
    verbose_name = 'Документы'

    def ready(self):
        import cloudinary
        from django.conf import settings

        import documents.signals  # noqa: F401

        credentials = getattr(settings, 'CLOUDINARY_CREDENTIALS', None)
        if credentials:
            cloudinary.config(
                cloud_name=credentials['CLOUD_NAME'],
                api_key=credentials['API_KEY'],
                api_secret=credentials['API_SECRET'],
                secure=True,
            )
