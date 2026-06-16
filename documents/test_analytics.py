from datetime import date, datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from documents.analytics import build_dashboard_analytics, get_period_range, get_monthly_amounts
from documents.models import Category, Document, Tag


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

    def test_company_type_stats_and_breakdown(self):
        Document.objects.create(
            title='Too doc',
            category=self.category,
            company_type='too',
            created_at=timezone.make_aware(datetime(2026, 6, 12, 12, 0)),
        )
        Document.objects.create(
            title='Ip doc',
            category=self.category,
            company_type='ip',
            created_at=timezone.make_aware(datetime(2026, 6, 14, 12, 0)),
        )
        data = build_dashboard_analytics('current_month', 12, date(2026, 6, 15))
        self.assertEqual(data['stats']['too_docs'], 1)
        self.assertEqual(data['stats']['ip_docs'], 1)
        self.assertEqual(data['stats']['ao_docs'], 0)
        keys = {item['key'] for item in data['company_types']}
        self.assertEqual(keys, {'too', 'ip'})

    def test_tag_breakdown(self):
        supplier = Tag.objects.create(name='Поставщик')
        contractor = Tag.objects.create(name='Исполнитель')
        doc1 = Document.objects.create(
            title='Supplier doc',
            category=self.category,
            created_at=timezone.make_aware(datetime(2026, 6, 11, 12, 0)),
        )
        doc2 = Document.objects.create(
            title='Contractor doc',
            category=self.category,
            created_at=timezone.make_aware(datetime(2026, 6, 13, 12, 0)),
        )
        doc1.tags.add(supplier)
        doc2.tags.add(contractor, supplier)
        data = build_dashboard_analytics('current_month', 12, date(2026, 6, 15))
        tag_names = {item['name']: item['doc_count'] for item in data['tags']}
        self.assertEqual(tag_names.get('Поставщик'), 2)
        self.assertEqual(tag_names.get('Исполнитель'), 1)
