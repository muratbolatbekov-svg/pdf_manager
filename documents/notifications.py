import json
import re
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.utils import timezone


TELEGRAM_CHAT_ID_PATTERN = re.compile(r'^-?\d+$')
TELEGRAM_BOT_LINK_PATTERN = re.compile(
    r'(?:https?://)?(?:t\.me|telegram\.me)/([A-Za-z0-9_]+)',
    re.IGNORECASE,
)


def parse_telegram_chat_id(value):
    """Accept numeric Chat ID or a t.me bot/username link (stored as username reference)."""
    raw = (value or '').strip()
    if not raw:
        return ''

    if TELEGRAM_CHAT_ID_PATTERN.match(raw):
        return raw

    match = TELEGRAM_BOT_LINK_PATTERN.search(raw)
    if match:
        username = match.group(1)
        if username.lower().endswith('bot'):
            raise ValidationError(
                'Укажите ваш Chat ID (число), а не ссылку на бота. '
                'Получите ID через @userinfobot в Telegram.'
            )
        return f'@{username}'

    raise ValidationError(
        'Укажите числовой Chat ID или ссылку вида https://t.me/username.'
    )


def get_app_base_url():
    app_url = getattr(settings, 'APP_URL', '').strip()
    if app_url:
        return app_url.rstrip('/')
    origins = getattr(settings, 'CSRF_TRUSTED_ORIGINS', [])
    if origins:
        return origins[0].rstrip('/')
    return 'http://127.0.0.1:8000'


def build_expiry_message(document, days_left):
    category = document.category.name if document.category else '—'
    end_date = document.end_date.strftime('%d.%m.%Y') if document.end_date else '—'
    base_url = get_app_base_url()
    doc_url = f'{base_url}/documents/{document.slug}/'

    if days_left == 0:
        subject = 'Договор истекает сегодня'
        lead = 'истекает сегодня'
    else:
        subject = f'Договор истекает через {days_left} дн.'
        lead = f'истекает через {days_left} дн. ({end_date})'

    body = (
        f'Договор «{document.title}» (категория: {category}) {lead}.\n'
        f'Перейдите в систему для продления.\n\n'
        f'Открыть документ: {doc_url}'
    )
    return subject, body


def send_expiry_email(recipient, document, days_left):
    if not recipient:
        return False
    subject, body = build_expiry_message(document, days_left)
    send_mail(
        subject=f'PDF Data Base: {subject}',
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
        fail_silently=False,
    )
    return True


def send_expiry_telegram(chat_id, document, days_left):
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '').strip()
    if not token or not chat_id:
        return False

    if chat_id.startswith('@'):
        return False

    subject, body = build_expiry_message(document, days_left)
    text = f'*{subject}*\n\n{body}'
    payload = urllib.parse.urlencode({
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': 'false',
    }).encode()

    request = urllib.request.Request(
        f'https://api.telegram.org/bot{token}/sendMessage',
        data=payload,
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode())
            return bool(data.get('ok'))
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        return False


def expiring_documents_queryset(days_ahead=None):
    from .models import Document

    today = timezone.localdate()
    if days_ahead is None:
        days_ahead = getattr(settings, 'CONTRACT_EXPIRY_WARNING_DAYS', 30)
    return Document.objects.filter(
        status='active',
        end_date__gte=today,
        end_date__lte=today + timezone.timedelta(days=days_ahead),
    )
