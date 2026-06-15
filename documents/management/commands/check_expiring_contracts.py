from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from documents.models import Document


class Command(BaseCommand):
    help = 'Отправляет уведомления о договорах, срок которых истекает в ближайшие дни'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=getattr(settings, 'CONTRACT_EXPIRY_WARNING_DAYS', 30),
            help='За сколько дней до окончания предупреждать',
        )

    def handle(self, *args, **options):
        days = options['days']
        today = timezone.localdate()
        deadline = today + timezone.timedelta(days=days)

        expiring = Document.objects.filter(
            status='active',
            end_date__gte=today,
            end_date__lte=deadline,
        ).select_related('category')

        expired = Document.objects.filter(status='active', end_date__lt=today)

        if not expiring.exists() and not expired.exists():
            self.stdout.write('Нет договоров для уведомления.')
            return

        lines = []
        if expiring.exists():
            lines.append(f'Договоры, истекающие в ближайшие {days} дней:')
            for doc in expiring:
                lines.append(f'  - {doc.title} (до {doc.end_date:%d.%m.%Y})')

        if expired.exists():
            lines.append('Просроченные договоры:')
            for doc in expired:
                lines.append(f'  - {doc.title} (истёк {doc.end_date:%d.%m.%Y})')

        message = '\n'.join(lines)
        self.stdout.write(message)

        notify_email = getattr(settings, 'NOTIFY_EMAIL', '')
        if notify_email:
            send_mail(
                subject='PDF Data Base: уведомление о сроках договоров',
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[notify_email],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f'Письмо отправлено на {notify_email}'))
