from datetime import date, datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from documents.analytics import build_dashboard_analytics, get_period_range, get_monthly_amounts
from documents.models import Category, Document


class AnalyticsTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Договоры')
        Document.objects.create(
            title='Jan doc',
            category=self.category,
            amount=Decimal('100000'),
            status='active',
            created_at=timezone.make_aware(datetime(2026, 1, 15, 12, 0)),
        )
        Document.objects.create(
            title='Jun doc',
            category=self.category,
            amount=Decimal('200000'),
            status='draft',
            with_vat=True,
            created_at=timezone.make_aware(datetime(2026, 6, 10, 12, 0)),
        )

    def test_current_month_stats(self):
        _, start, end = get_period_range('current_month', date(2026, 6, 15))
        data = build_dashboard_analytics('current_month', 12, date(2026, 6, 15))
        self.assertEqual(start, date(2026, 6, 1))
        self.assertEqual(end, date(2026, 6, 30))
        self.assertEqual(data['stats']['total_docs'], 1)
        self.assertEqual(data['stats']['draft_docs'], 1)
        self.assertEqual(data['stats']['with_vat_docs'], 1)
        self.assertEqual(data['stats']['without_vat_docs'], 0)

    def test_monthly_amounts_includes_june(self):
        points = get_monthly_amounts(date(2026, 6, 30), 3)
        labels = [p['label'] for p in points]
        self.assertIn('Июн 2026', labels)
        june = next(p for p in points if p['label'] == 'Июн 2026')
        self.assertEqual(june['amount'], 200000.0)

    def test_category_breakdown_percent(self):
        data = build_dashboard_analytics('current_year', 12, date(2026, 6, 15))
        self.assertEqual(len(data['categories']), 1)
        self.assertEqual(data['categories'][0]['name'], 'Договоры')
        self.assertEqual(data['categories'][0]['percent'], 100.0)
