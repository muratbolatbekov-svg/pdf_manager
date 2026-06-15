from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Проверяет подключение к Cloudinary'

    def handle(self, *args, **options):
        import cloudinary.api

        try:
            response = cloudinary.api.ping()
            self.stdout.write(self.style.SUCCESS(f'Cloudinary OK: {response}'))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'Cloudinary error: {exc}'))
            raise SystemExit(1) from exc
