import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from documents.models import Document, DocumentComment, Tag, UserProfile
from documents.utils import parse_tags, user_initials
from documents.views import document_comment_create, document_comment_delete, document_list, tag_autocomplete


class TagFeatureTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='manager', password='pass12345')
        UserProfile.objects.filter(user=self.user).update(role=UserProfile.ROLE_MANAGER)
        self.tag = Tag.objects.create(name='urgent')
        self.document = Document.objects.create(title='Doc', amount=Decimal('1000'))
        self.document.tags.add(self.tag)

    def test_tag_autocomplete(self):
        Tag.objects.create(name='urgency')
        request = RequestFactory().get('/documents/tags/autocomplete/', {'q': 'urg'})
        request.user = self.user
        response = tag_autocomplete(request)
        data = json.loads(response.content)
        self.assertIn('urgent', data['tags'])
        self.assertIn('urgency', data['tags'])

    def test_filter_by_tag(self):
        other = Document.objects.create(title='Other')
        request = RequestFactory().get('/documents/', {'tag': str(self.tag.pk)})
        request.user = self.user
        response = document_list(request)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Doc', content)
        self.assertNotIn('Other', content)

    def test_parse_tags_comma_semicolon(self):
        self.assertEqual(parse_tags('a, b; c'), ['a', 'b', 'c'])


class CommentTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='manager', password='pass12345', first_name='Ivan', last_name='Ivanov')
        UserProfile.objects.filter(user=self.user).update(role=UserProfile.ROLE_MANAGER)
        self.admin = User.objects.create_user(username='admin', password='pass12345')
        UserProfile.objects.filter(user=self.admin).update(role=UserProfile.ROLE_ADMIN)
        self.document = Document.objects.create(title='Doc', slug='doc')

    def test_create_comment(self):
        request = self.factory.post(reverse('document_comment_create', kwargs={'slug': 'doc'}), {'text': 'Hello'})
        request.user = self.user
        response = document_comment_create(request, slug='doc')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['comment']['text'], 'Hello')
        self.assertEqual(DocumentComment.objects.count(), 1)

    def test_delete_own_comment(self):
        comment = DocumentComment.objects.create(document=self.document, user=self.user, text='x')
        request = self.factory.post(
            reverse('document_comment_delete', kwargs={'slug': 'doc', 'comment_id': comment.pk})
        )
        request.user = self.user
        response = document_comment_delete(request, slug='doc', comment_id=comment.pk)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(DocumentComment.objects.filter(pk=comment.pk).exists())

    def test_admin_can_delete_any_comment(self):
        comment = DocumentComment.objects.create(document=self.document, user=self.user, text='x')
        request = self.factory.post(
            reverse('document_comment_delete', kwargs={'slug': 'doc', 'comment_id': comment.pk})
        )
        request.user = self.admin
        response = document_comment_delete(request, slug='doc', comment_id=comment.pk)
        self.assertEqual(response.status_code, 200)

    def test_user_initials(self):
        self.assertEqual(user_initials(self.user), 'II')
