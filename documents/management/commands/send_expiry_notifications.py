from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from documents.models import Document, UserNotificationSettings
from documents.notifications import send_expiry_email, send_expiry_telegram


THRESHOLDS = (
    (30, 'notify_30_days'),
    (7, 'notify_7_days'),
    (0, 'notify_on_expiry_day'),
)


class Command(BaseCommand):
    help = 'Отправляет персональные уведомления о сроках договоров (cron: 09:00 Asia/Almaty)'

    def handle(self, *args, **options):
        today = timezone.localdate()
        user_settings = UserNotificationSettings.objects.select_related('user').filter(
            user__is_active=True,
        )

        sent_email = 0
        sent_telegram = 0
        skipped = 0

        for prefs in user_settings:
            if not prefs.notifications_enabled:
                continue
            if not any(getattr(prefs, field) for _, field in THRESHOLDS):
                continue

            for days_left, field_name in THRESHOLDS:
                if not getattr(prefs, field_name):
                    continue

                target_date = today + timezone.timedelta(days=days_left)
                documents = Document.objects.filter(
                    status='active',
                    end_date=target_date,
                ).select_related('category')

                for document in documents:
                    delivered = False
                    if prefs.notify_email_enabled and prefs.notify_email:
                        try:
                            send_expiry_email(prefs.notify_email, document, days_left)
                            sent_email += 1
                            delivered = True
                        except Exception as exc:
                            self.stderr.write(
                                f'Email ошибка ({prefs.user.username}, {document.slug}): {exc}'
                            )

                    if prefs.notify_telegram_enabled and prefs.telegram_chat_id:
                        if send_expiry_telegram(prefs.telegram_chat_id, document, days_left):
                            sent_telegram += 1
                            delivered = True
                        elif prefs.telegram_chat_id.startswith('@'):
                            self.stderr.write(
                                f'Telegram: для {prefs.user.username} нужен числовой Chat ID, не username.'
                            )

                    if not delivered:
                        skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Готово: email={sent_email}, telegram={sent_telegram}, без доставки={skipped}'
            )
        )

        if not getattr(settings, 'TELEGRAM_BOT_TOKEN', '').strip():
            self.stdout.write(
                self.style.WARNING('TELEGRAM_BOT_TOKEN не задан — Telegram-уведомления пропущены.')
            )
