import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy

from .models import Category, Document


PERIOD_CHOICES = [
    ('current_month', _lazy('Текущий месяц')),
    ('prev_month', _lazy('Прошлый месяц')),
    ('current_quarter', _lazy('Текущий квартал')),
    ('prev_quarter', _lazy('Прошлый квартал')),
    ('current_year', _lazy('Текущий год')),
]

PERIOD_KEYS = {key for key, _ in PERIOD_CHOICES}

MONTH_ABBR = [
    _lazy('Янв'), _lazy('Фев'), _lazy('Мар'), _lazy('Апр'), _lazy('Май'), _lazy('Июн'),
    _lazy('Июл'), _lazy('Авг'), _lazy('Сен'), _lazy('Окт'), _lazy('Ноя'), _lazy('Дек'),
]


def _last_day_of_month(year, month):
    return date(year, month, calendar.monthrange(year, month)[1])


def _quarter_bounds(year, quarter):
    start_month = (quarter - 1) * 3 + 1
    end_month = start_month + 2
    return date(year, start_month, 1), _last_day_of_month(year, end_month)


def get_period_range(period_key, today=None):
    today = today or timezone.localdate()
    if period_key not in PERIOD_KEYS:
        period_key = 'current_month'

    if period_key == 'current_month':
        start = today.replace(day=1)
        end = _last_day_of_month(today.year, today.month)
    elif period_key == 'prev_month':
        if today.month == 1:
            year, month = today.year - 1, 12
        else:
            year, month = today.year, today.month - 1
        start = date(year, month, 1)
        end = _last_day_of_month(year, month)
    elif period_key == 'current_quarter':
        quarter = (today.month - 1) // 3 + 1
        start, end = _quarter_bounds(today.year, quarter)
    elif period_key == 'prev_quarter':
        quarter = (today.month - 1) // 3 + 1
        if quarter == 1:
            start, end = _quarter_bounds(today.year - 1, 4)
        else:
            start, end = _quarter_bounds(today.year, quarter - 1)
    else:
        start = date(today.year, 1, 1)
        end = date(today.year, 12, 31)

    return period_key, start, end


def _documents_in_period(start, end):
    return Document.objects.filter(
        created_at__date__gte=start,
        created_at__date__lte=end,
    )


def get_period_stats(start, end):
    qs = _documents_in_period(start, end)
    return {
        'total_docs': qs.count(),
        'active_docs': qs.filter(status='active').count(),
        'draft_docs': qs.filter(status='draft').count(),
        'archived_docs': qs.filter(status='archived').count(),
        'with_vat_docs': qs.filter(with_vat=True).count(),
        'without_vat_docs': qs.filter(with_vat=False).count(),
    }


def get_monthly_amounts(end_date, months_count):
    months_count = months_count if months_count in (3, 6, 12) else 12
    start_month = end_date.replace(day=1)
    for _ in range(months_count - 1):
        if start_month.month == 1:
            start_month = date(start_month.year - 1, 12, 1)
        else:
            start_month = date(start_month.year, start_month.month - 1, 1)

    range_end = _last_day_of_month(end_date.year, end_date.month)
    qs = (
        Document.objects.filter(
            created_at__date__gte=start_month,
            created_at__date__lte=range_end,
        )
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )
    totals_by_month = {
        row['month'].date().replace(day=1): row['total'] or Decimal('0')
        for row in qs
        if row['month']
    }

    points = []
    cursor = start_month
    while cursor <= range_end:
        month_end = _last_day_of_month(cursor.year, cursor.month)
        if month_end > range_end:
            month_end = range_end
        label = f'{MONTH_ABBR[cursor.month - 1]} {cursor.year}'
        amount = float(totals_by_month.get(cursor, Decimal('0')))
        points.append({'label': label, 'amount': amount, 'month': cursor.isoformat()})
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)

    return points


def get_category_breakdown(start, end):
    qs = (
        Document.objects.filter(
            created_at__date__gte=start,
            created_at__date__lte=end,
        )
        .values('category__name')
        .annotate(total_amount=Sum('amount'), doc_count=Count('id'))
        .filter(total_amount__gt=0)
        .order_by('-total_amount')
    )
    grand_total = sum((row['total_amount'] or Decimal('0')) for row in qs)
    items = []
    for row in qs:
        amount = row['total_amount'] or Decimal('0')
        name = row['category__name'] or _('Без категории')
        pct = float(amount / grand_total * 100) if grand_total else 0.0
        items.append({
            'name': name,
            'amount': float(amount),
            'amount_formatted': f'{amount:,.0f}'.replace(',', ' '),
            'percent': round(pct, 1),
            'label': f'{name} — {amount:,.0f} ₸ ({pct:.1f}%)'.replace(',', ' '),
            'doc_count': row['doc_count'],
        })
    return items, float(grand_total)


def build_dashboard_analytics(period_key='current_month', months_count=12, today=None):
    today = today or timezone.localdate()
    period_key, start, end = get_period_range(period_key, today)
    stats = get_period_stats(start, end)
    trend = get_monthly_amounts(end, months_count)
    categories, category_total = get_category_breakdown(start, end)
    period_label = dict(PERIOD_CHOICES).get(period_key, period_key)
    return {
        'period': period_key,
        'period_label': period_label,
        'period_start': start.isoformat(),
        'period_end': end.isoformat(),
        'months': months_count,
        'stats': stats,
        'trend': trend,
        'categories': categories,
        'category_total': category_total,
    }
