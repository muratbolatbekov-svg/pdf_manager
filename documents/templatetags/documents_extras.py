from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def last_login_label(value):
    if not value:
        return '—'
    local_dt = timezone.localtime(value)
    login_date = local_dt.date()
    today = timezone.localdate()
    if login_date == today:
        return 'сегодня'
    if login_date == today - timezone.timedelta(days=1):
        return 'вчера'
    return local_dt.strftime('%d.%m.%Y')


@register.filter
def user_display_name(user):
    name = user.get_full_name().strip()
    return name if name else user.username
