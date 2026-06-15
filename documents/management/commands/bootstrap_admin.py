import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from documents.models import UserProfile


class Command(BaseCommand):
    help = 'Создаёт или обновляет администратора из переменных ADMIN_USERNAME и ADMIN_PASSWORD'

    def handle(self, *args, **options):
        username = os.environ.get('ADMIN_USERNAME', 'admin')
        password = os.environ.get('ADMIN_PASSWORD')

        if not password:
            self.stdout.write('ADMIN_PASSWORD не задан — пропуск.')
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'is_staff': True, 'is_superuser': True},
        )
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save()

        UserProfile.objects.update_or_create(
            user=user,
            defaults={'role': UserProfile.ROLE_ADMIN},
        )

        action = 'создан' if created else 'обновлён'
        self.stdout.write(self.style.SUCCESS(f'Администратор «{username}» {action}.'))
