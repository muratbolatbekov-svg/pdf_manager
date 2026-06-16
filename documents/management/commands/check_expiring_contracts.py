from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Устаревшая команда — используйте send_expiry_notifications'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Перенаправление на send_expiry_notifications...'))
        call_command('send_expiry_notifications')
