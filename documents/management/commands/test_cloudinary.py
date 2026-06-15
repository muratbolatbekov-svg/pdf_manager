from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Проверяет подключение к Cloudinary'

    def handle(self, *args, **options):
        import cloudinary
        import cloudinary.api
        import cloudinary.uploader

        credentials = settings.CLOUDINARY_CREDENTIALS
        self.stdout.write(
            f"Cloud name: {credentials['CLOUD_NAME']}\n"
            f"API key: {credentials['API_KEY'][:4]}...{credentials['API_KEY'][-4:]}\n"
            f"Upload resource_type: {settings.CLOUDINARY_UPLOAD_RESOURCE_TYPE}\n"
            f"Upload preset: {settings.CLOUDINARY_UPLOAD_PRESET or '(signed upload)'}"
        )

        cloudinary.config(
            cloud_name=credentials['CLOUD_NAME'],
            api_key=credentials['API_KEY'],
            api_secret=credentials['API_SECRET'],
            secure=True,
        )

        try:
            response = cloudinary.api.ping()
            self.stdout.write(self.style.SUCCESS(f'Cloudinary ping OK: {response}'))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'Cloudinary ping error: {exc}'))
            raise SystemExit(1) from exc

        upload_options = {
            'folder': 'pdfs',
            'resource_type': settings.CLOUDINARY_UPLOAD_RESOURCE_TYPE,
            'use_filename': True,
        }
        if settings.CLOUDINARY_UPLOAD_PRESET:
            upload_options['upload_preset'] = settings.CLOUDINARY_UPLOAD_PRESET

        try:
            test_file = ContentFile(b'%PDF-1.4 test', name='test.pdf')
            upload_response = cloudinary.uploader.upload(test_file, **upload_options)
            public_id = upload_response.get('public_id')
            self.stdout.write(self.style.SUCCESS(f'Upload test OK: {public_id}'))
            cloudinary.uploader.destroy(public_id, resource_type=upload_response.get('resource_type', 'raw'))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'Upload test error: {exc}'))
            raise SystemExit(1) from exc
