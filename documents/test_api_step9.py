import json

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from documents.models import ApiKey, Category, Document, UserProfile
from documents.views import api_key_create, api_settings


class ApiKeyTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = User.objects.create_user(username='admin', password='pass12345')
        UserProfile.objects.filter(user=self.admin).update(role=UserProfile.ROLE_ADMIN)

    def test_create_and_authenticate_key(self):
        _, raw = ApiKey.create_key('Test key', self.admin)
        self.assertTrue(raw.startswith('sk-'))
        api_key = ApiKey.authenticate(raw)
        self.assertIsNotNone(api_key)
        self.assertEqual(api_key.name, 'Test key')

    def test_masked_key_format(self):
        obj, _ = ApiKey.create_key('Mask test', self.admin)
        self.assertTrue(obj.masked_key.startswith('sk-...'))

    def test_bearer_api_access(self):
        _, raw = ApiKey.create_key('Integration', self.admin)
        Document.objects.create(title='API Doc')
        response = self.client.get(
            '/api/documents/',
            HTTP_AUTHORIZATION=f'Bearer {raw}',
        )
        self.assertEqual(response.status_code, 200)

    def test_api_stats(self):
        _, raw = ApiKey.create_key('Stats', self.admin)
        response = self.client.get(
            '/api/stats/',
            HTTP_AUTHORIZATION=f'Bearer {raw}',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('total_documents', data)

    def test_api_filters(self):
        category = Category.objects.create(name='Cat')
        Document.objects.create(title='Match', category=category, status='active')
        Document.objects.create(title='Other', status='draft')
        _, raw = ApiKey.create_key('Filter', self.admin)
        response = self.client.get(
            '/api/documents/?category=' + str(category.pk) + '&status=active&search=Match',
            HTTP_AUTHORIZATION=f'Bearer {raw}',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        results = data.get('results', data)
        if isinstance(results, dict):
            results = results.get('results', [])
        titles = [item['title'] for item in results]
        self.assertIn('Match', titles)
        self.assertNotIn('Other', titles)

    def test_api_settings_page(self):
        request = self.factory.get('/settings/api/')
        request.user = self.admin
        request.session = {}
        response = api_settings(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('API-ключ', response.content.decode())

    def test_api_key_create_view(self):
        request = self.factory.post('/settings/api/create/', {'name': 'New Key'})
        request.user = self.admin
        request.session = {}
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.contrib.messages.middleware import MessageMiddleware
        MessageMiddleware(lambda r: None).process_request(request)
        request._messages = FallbackStorage(request)
        response = api_key_create(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ApiKey.objects.count(), 1)
        self.assertIn('new_api_key', request.session)

    def test_swagger_schema(self):
        _, raw = ApiKey.create_key('Docs', self.admin)
        response = self.client.get(
            '/api/schema/',
            HTTP_AUTHORIZATION=f'Bearer {raw}',
        )
        self.assertEqual(response.status_code, 200)

    def test_invalid_bearer_token(self):
        response = self.client.get(
            '/api/documents/',
            HTTP_AUTHORIZATION='Bearer sk-invalid-token',
        )
        self.assertEqual(response.status_code, 401)
