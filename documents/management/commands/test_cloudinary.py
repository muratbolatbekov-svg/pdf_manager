from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Проверяет подключение к Cloudinary'

    def handle(self, *args, **options):
        import cloudinary
        import cloudinary.api

        credentials = settings.CLOUDINARY_CREDENTIALS
        self.stdout.write(
            f"Cloud name: {credentials['CLOUD_NAME']}\n"
            f"API key: {credentials['API_KEY'][:4]}...{credentials['API_KEY'][-4:]}\n"
            f"API secret: {'*' * 8}{credentials['API_SECRET'][-4:]}"
        )

        cloudinary.config(
            cloud_name=credentials['CLOUD_NAME'],
            api_key=credentials['API_KEY'],
            api_secret=credentials['API_SECRET'],
            secure=True,
        )

        try:
            response = cloudinary.api.ping()
            self.stdout.write(self.style.SUCCESS(f'Cloudinary OK: {response}'))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'Cloudinary error: {exc}'))
            self.stdout.write(
                'Проверьте, что API Key и API Secret из одной пары в Cloudinary Dashboard.'
            )
            raise SystemExit(1) from exc
