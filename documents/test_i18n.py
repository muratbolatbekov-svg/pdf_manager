from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import translation

from documents.middleware import SESSION_LANGUAGE_KEY

from documents.models import Document, UserProfile
from documents.views import dashboard, document_list


class LanguageSwitchTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user('viewer', password='pass12345')
        UserProfile.objects.filter(user=self.user).update(role=UserProfile.ROLE_VIEWER)

    def test_set_language_persists_in_session(self):
        self.client.login(username='viewer', password='pass12345')
        response = self.client.post(
            reverse('set_language'),
            {'language': 'en', 'next': '/'},
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get(SESSION_LANGUAGE_KEY), 'en')

    def test_english_dashboard_menu(self):
        request = self.factory.get('/dashboard/')
        request.user = self.user
        request.session = {}
        with translation.override('en'):
            response = dashboard(request)
        content = response.content.decode()
        self.assertIn('Dashboard', content)
        self.assertNotIn('>Дашборд<', content)

    def test_kazakh_status_label(self):
        Document.objects.create(title='Test', status='active')
        request = self.factory.get('/documents/')
        request.user = self.user
        request.session = {}
        request.GET = request.GET.copy()
        with translation.override('kk'):
            response = document_list(request)
        content = response.content.decode()
        self.assertIn('Белсенді', content)
