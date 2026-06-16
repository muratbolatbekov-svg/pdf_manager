import json
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.auth.tokens import default_token_generator
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.http import Http404
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils import timezone

from datetime import date

from documents.models import AuditLog, Category, Document, UserNotificationSettings, UserProfile
from documents.notifications import parse_telegram_chat_id
from documents.utils import generate_unique_slug, parse_tags
from documents.views import (
    document_create,
    document_detail,
    document_list,
    document_pdf_preview,
    dashboard,
    dashboard_analytics,
    document_export,
    home,
    notification_settings,
    user_list,
)


class SlugUtilsTests(TestCase):
    def test_cyrillic_slug(self):
        slug = generate_unique_slug('Договор поставки')
        self.assertTrue(slug)

    def test_unique_slug_collision(self):
        Document.objects.create(title='Test Doc', slug='test-doc')
        slug = generate_unique_slug('Test Doc')
        self.assertEqual(slug, 'test-doc-2')


class TagUtilsTests(TestCase):
    def test_parse_tags(self):
        self.assertEqual(parse_tags('a, b; c'), ['a', 'b', 'c'])


class DocumentViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='manager', password='pass12345')
        UserProfile.objects.filter(user=self.user).update(role=UserProfile.ROLE_MANAGER)
        self.admin = User.objects.create_user(username='admin', password='pass12345')
        UserProfile.objects.filter(user=self.admin).update(role=UserProfile.ROLE_ADMIN)
        self.category = Category.objects.create(name='Договоры')
        self.document = Document.objects.create(
            title='Тестовый договор',
            category=self.category,
            amount=Decimal('100000'),
            status='active',
        )

    def test_login_required(self):
        response = self.client.get(reverse('document_list'))
        self.assertEqual(response.status_code, 302)

    def test_home_public(self):
        request = self.factory.get('/')
        request.user = AnonymousUser()
        response = home(request)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('PDF Data Base', content)
        self.assertIn('Войти', content)
        self.assertNotIn('Быстрые действия', content)

    def test_home_authenticated(self):
        request = self.factory.get('/')
        request.user = self.user
        response = home(request)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Статистика', content)
        self.assertIn('Быстрые действия', content)
        self.assertIn('Открыть дашборд', content)

    def test_pdf_preview_requires_auth(self):
        response = self.client.get(reverse('document_pdf_preview', kwargs={'slug': self.document.slug}))
        self.assertEqual(response.status_code, 302)

    def test_pdf_preview_no_file(self):
        request = self.factory.get(f'/documents/{self.document.slug}/preview/')
        request.user = self.user
        with self.assertRaises(Http404):
            document_pdf_preview(request, slug=self.document.slug)

    def test_document_list_has_pdf_viewer(self):
        request = self.factory.get('/documents/')
        request.user = self.user
        response = document_list(request)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('pdf-preview-trigger', content)
        self.assertIn('pdfViewerModal', content)
        self.assertIn('document-filters.js', content)

    def test_document_list(self):
        request = self.factory.get('/documents/')
        request.user = self.user
        response = document_list(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Тестовый договор', response.content.decode())

    def test_document_detail_by_slug(self):
        request = self.factory.get(f'/documents/{self.document.slug}/')
        request.user = self.user
        response = document_detail(request, slug=self.document.slug)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Тестовый договор', response.content.decode())

    def test_viewer_cannot_create(self):
        viewer = User.objects.create_user(username='viewer', password='pass12345')
        UserProfile.objects.filter(user=viewer).update(role=UserProfile.ROLE_VIEWER)
        request = self.factory.get('/documents/create/')
        request.user = viewer
        with self.assertRaises(PermissionDenied):
            document_create(request)

    def test_manager_can_create(self):
        request = self.factory.get('/documents/create/')
        request.user = self.user
        response = document_create(request)
        self.assertEqual(response.status_code, 200)

    def test_document_list_search_ui(self):
        request = self.factory.get('/documents/')
        request.user = self.user
        response = document_list(request)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('docSearchInput', content)
        self.assertIn('doc-row', content)
        self.assertIn('Тестовый договор', content)

    def test_document_filters_by_status(self):
        request = self.factory.get('/documents/', {'status': 'active'})
        request.user = self.user
        response = document_list(request)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('filter-tag', content)
        self.assertIn('Активный', content)

    def test_dashboard_expiring_card(self):
        today = timezone.localdate()
        Document.objects.filter(pk=self.document.pk).update(
            end_date=today + timezone.timedelta(days=10),
            status='active',
        )
        request = self.factory.get('/dashboard/')
        request.user = self.user
        response = dashboard(request)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Истекает в', content)
        self.assertIn('date_from=', content)
        self.assertIn('Аналитика', content)
        self.assertIn('amountTrendChart', content)

    def test_dashboard_analytics_json(self):
        request = self.factory.get('/dashboard/analytics/', {'period': 'current_month', 'months': '6'})
        request.user = self.user
        response = dashboard_analytics(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('stats', data)
        self.assertIn('trend', data)
        self.assertIn('categories', data)
        self.assertEqual(data['months'], 6)

    def test_document_export_xlsx(self):
        request = self.factory.get('/documents/export/?format=xlsx')
        request.user = self.user
        response = document_export(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            response['Content-Type'],
        )
        self.assertIn('documents_', response['Content-Disposition'])
        self.assertIn('.xlsx', response['Content-Disposition'])

    def test_notification_settings_page(self):
        request = self.factory.get('/settings/notifications/')
        request.user = self.user
        response = notification_settings(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Настройки', response.content.decode())

    def test_notification_settings_save(self):
        UserNotificationSettings.objects.get_or_create(
            user=self.user,
            defaults={'notify_email': 'old@example.com'},
        )
        self.client.login(username='manager', password='pass12345')
        response = self.client.post(reverse('notification_settings'), {
            'notify_email_enabled': 'on',
            'notify_email': 'user@example.com',
            'notify_telegram_enabled': '',
            'telegram_chat_id': '',
            'notify_30_days': 'on',
            'notify_7_days': 'on',
            'notify_on_expiry_day': '',
            'dashboard_expiry_days': '14',
        })
        self.assertEqual(response.status_code, 302)
        prefs = UserNotificationSettings.objects.get(user=self.user)
        self.assertEqual(prefs.notify_email, 'user@example.com')
        self.assertEqual(prefs.dashboard_expiry_days, 14)

    def test_parse_telegram_chat_id(self):
        self.assertEqual(parse_telegram_chat_id('123456789'), '123456789')
        self.assertEqual(parse_telegram_chat_id('-1001234567890'), '-1001234567890')
        with self.assertRaises(ValidationError):
            parse_telegram_chat_id('https://t.me/MyBot')

    def test_admin_can_delete(self):
        self.client.login(username='admin', password='pass12345')
        slug = self.document.slug
        response = self.client.post(reverse('document_delete', kwargs={'slug': slug}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Document.objects.filter(slug=slug).exists())
        self.assertTrue(AuditLog.objects.filter(action='delete', object_repr__contains='Тестовый').exists())


class UserManagementTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.admin = User.objects.create_user(username='admin', password='pass12345', email='admin@example.com')
        UserProfile.objects.filter(user=self.admin).update(role=UserProfile.ROLE_ADMIN)
        self.manager = User.objects.create_user(username='manager', password='pass12345', email='mgr@example.com')
        UserProfile.objects.filter(user=self.manager).update(role=UserProfile.ROLE_MANAGER)

    def test_user_list_admin_only(self):
        request = self.factory.get('/settings/users/')
        request.user = self.manager
        with self.assertRaises(PermissionDenied):
            user_list(request)

    def test_user_list_renders_for_admin(self):
        request = self.factory.get('/settings/users/')
        request.user = self.admin
        response = user_list(request)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Пригласить пользователя', content)
        self.assertIn('mgr@example.com', content)

    def test_admin_can_update_role(self):
        self.client.login(username='admin', password='pass12345')
        response = self.client.post(
            reverse('user_update_role', kwargs={'user_id': self.manager.pk}),
            {'role': UserProfile.ROLE_VIEWER},
        )
        self.assertEqual(response.status_code, 302)
        self.manager.profile.refresh_from_db()
        self.assertEqual(self.manager.profile.role, UserProfile.ROLE_VIEWER)

    def test_admin_cannot_change_own_role(self):
        self.client.login(username='admin', password='pass12345')
        response = self.client.post(
            reverse('user_update_role', kwargs={'user_id': self.admin.pk}),
            {'role': UserProfile.ROLE_VIEWER},
        )
        self.assertEqual(response.status_code, 302)
        self.admin.profile.refresh_from_db()
        self.assertEqual(self.admin.profile.role, UserProfile.ROLE_ADMIN)

    def test_invite_saves_full_name(self):
        self.client.login(username='admin', password='pass12345')
        response = self.client.post(
            reverse('user_invite'),
            {
                'full_name': 'Иван Петров',
                'email': 'ivan@example.com',
                'role': UserProfile.ROLE_VIEWER,
            },
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email='ivan@example.com')
        self.assertEqual(user.profile.full_name, 'Иван Петров')

    def test_user_rename(self):
        self.manager.profile.full_name = 'Старое имя'
        self.manager.profile.save()
        self.client.login(username='admin', password='pass12345')
        response = self.client.post(
            reverse('user_rename', kwargs={'user_id': self.manager.pk}),
            {'full_name': 'Новое ФИО'},
        )
        self.assertEqual(response.status_code, 302)
        self.manager.profile.refresh_from_db()
        self.assertEqual(self.manager.profile.full_name, 'Новое ФИО')

    def test_user_block_toggle(self):
        self.assertTrue(self.manager.is_active)
        self.client.login(username='admin', password='pass12345')
        self.client.post(reverse('user_block', kwargs={'user_id': self.manager.pk}))
        self.manager.refresh_from_db()
        self.assertFalse(self.manager.is_active)
        self.client.post(reverse('user_block', kwargs={'user_id': self.manager.pk}))
        self.manager.refresh_from_db()
        self.assertTrue(self.manager.is_active)

    def test_user_display_name_uses_profile_full_name(self):
        from documents.utils import get_user_display_name

        self.manager.profile.full_name = 'Алия Смагулова'
        self.manager.profile.save()
        self.assertEqual(get_user_display_name(self.manager), 'Алия Смагулова')

    def test_invite_set_password(self):
        invited = User(username='invite', email='invite@example.com')
        invited.set_unusable_password()
        invited.save()
        UserProfile.objects.update_or_create(user=invited, defaults={'role': UserProfile.ROLE_VIEWER})
        uid = urlsafe_base64_encode(force_bytes(invited.pk))
        token = default_token_generator.make_token(invited)
        response = self.client.post(
            reverse('invite_set_password', kwargs={'uidb64': uid, 'token': token}),
            {'password': 'newpass123', 'password2': 'newpass123'},
        )
        self.assertEqual(response.status_code, 302)
        invited.refresh_from_db()
        self.assertTrue(invited.check_password('newpass123'))


class DocumentFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='manager', password='pass12345')

    def test_pdf_validation_rejects_non_pdf(self):
        from documents.forms import DocumentForm

        bad_file = SimpleUploadedFile('test.txt', b'not a pdf', content_type='text/plain')
        form = DocumentForm(
            data={'title': 'Doc', 'amount': '0', 'status': 'active'},
            files={'pdf_file': bad_file},
            user=self.user,
        )
        self.assertFalse(form.is_valid())

    def test_file_size_handles_none_size(self):
        from documents.forms import DocumentForm
        from io import BytesIO

        class UploadedPdfStub:
            name = 'contract.pdf'
            content_type = 'application/pdf'
            size = None

            def __init__(self):
                self._buffer = BytesIO(b'%PDF-1.4 test content')

            def seek(self, pos, whence=0):
                return self._buffer.seek(pos, whence)

            def tell(self):
                return self._buffer.tell()

        form = DocumentForm(user=self.user)
        stub = UploadedPdfStub()
        self.assertEqual(form._file_size(stub), len(b'%PDF-1.4 test content'))
        self.assertIsNone(form._file_size(type('X', (), {'size': None})()))

    def test_end_date_before_start_date(self):
        from documents.forms import DocumentForm

        form = DocumentForm(
            data={
                'title': 'Doc',
                'amount': '0',
                'status': 'active',
                'start_date': '2026-06-15',
                'end_date': '2026-01-01',
            },
            user=self.user,
        )
        self.assertFalse(form.is_valid())


class CategoryViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username='admin', password='pass12345')
        UserProfile.objects.filter(user=self.admin).update(role=UserProfile.ROLE_ADMIN)
        self.category = Category.objects.create(name='Old')

    def test_category_edit(self):
        self.client.login(username='admin', password='pass12345')
        response = self.client.post(
            reverse('category_edit', kwargs={'pk': self.category.pk}),
            {'name': 'New Name', 'description': 'Updated'},
        )
        self.assertEqual(response.status_code, 302)
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, 'New Name')

    def test_category_delete(self):
        self.client.login(username='admin', password='pass12345')
        response = self.client.post(reverse('category_delete', kwargs={'pk': self.category.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Category.objects.filter(pk=self.category.pk).exists())


class ApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='apiuser', password='pass12345')
        UserProfile.objects.filter(user=self.user).update(role=UserProfile.ROLE_MANAGER)
        Document.objects.create(title='API Doc')

    def test_api_requires_auth(self):
        response = self.client.get('/api/documents/')
        self.assertIn(response.status_code, (401, 403))

    def test_api_list_session_auth(self):
        self.client.login(username='apiuser', password='pass12345')
        response = self.client.get('/api/documents/')
        self.assertEqual(response.status_code, 200)

    def test_api_categories(self):
        Category.objects.create(name='Test Cat')
        self.client.login(username='apiuser', password='pass12345')
        response = self.client.get('/api/categories/')
        self.assertEqual(response.status_code, 200)
