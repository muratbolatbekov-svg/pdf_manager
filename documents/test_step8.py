import json

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from documents.document_links import create_bidirectional_link, delete_bidirectional_link
from documents.models import Document, DocumentLink, UserProfile
from documents.views import document_link_create, document_link_delete, document_link_search


class DocumentLinkTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='manager', password='pass12345')
        UserProfile.objects.filter(user=self.user).update(role=UserProfile.ROLE_MANAGER)
        self.doc_a = Document.objects.create(title='Doc A', slug='doc-a')
        self.doc_b = Document.objects.create(title='Doc B', slug='doc-b')
        self.doc_c = Document.objects.create(title='Doc C', slug='doc-c')

    def test_bidirectional_link_created(self):
        link, created = create_bidirectional_link(self.doc_a, self.doc_b, DocumentLink.TYPE_ACT)
        self.assertTrue(created)
        self.assertEqual(link.link_type, DocumentLink.TYPE_ACT)
        self.assertTrue(DocumentLink.objects.filter(document=self.doc_a, linked=self.doc_b).exists())
        self.assertTrue(DocumentLink.objects.filter(document=self.doc_b, linked=self.doc_a).exists())

    def test_bidirectional_link_deleted(self):
        create_bidirectional_link(self.doc_a, self.doc_b, DocumentLink.TYPE_INVOICE)
        delete_bidirectional_link(self.doc_a, self.doc_b)
        self.assertFalse(DocumentLink.objects.filter(document=self.doc_a, linked=self.doc_b).exists())
        self.assertFalse(DocumentLink.objects.filter(document=self.doc_b, linked=self.doc_a).exists())

    def test_link_search_excludes_current_and_linked(self):
        create_bidirectional_link(self.doc_a, self.doc_b, DocumentLink.TYPE_OTHER)
        request = self.factory.get('/documents/doc-a/links/search/')
        request.user = self.user
        response = document_link_search(request, slug='doc-a')
        data = json.loads(response.content)
        ids = {item['id'] for item in data['results']}
        self.assertNotIn(self.doc_a.pk, ids)
        self.assertNotIn(self.doc_b.pk, ids)
        self.assertIn(self.doc_c.pk, ids)

    def test_create_link_via_api(self):
        request = self.factory.post(
            '/documents/doc-a/links/',
            {'link_type': DocumentLink.TYPE_SUPPLEMENT, 'linked_ids': [str(self.doc_c.pk)]},
        )
        request.user = self.user
        response = document_link_create(request, slug='doc-a')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(DocumentLink.objects.filter(document=self.doc_c, linked=self.doc_a).exists())

    def test_cannot_duplicate_link(self):
        create_bidirectional_link(self.doc_a, self.doc_b, DocumentLink.TYPE_OTHER)
        request = self.factory.post(
            '/documents/doc-a/links/',
            {'link_type': DocumentLink.TYPE_OTHER, 'linked_ids': [str(self.doc_b.pk)]},
        )
        request.user = self.user
        response = document_link_create(request, slug='doc-a')
        self.assertEqual(response.status_code, 400)

    def test_delete_link_via_api(self):
        link, _ = create_bidirectional_link(self.doc_a, self.doc_b, DocumentLink.TYPE_OTHER)
        request = self.factory.post(f'/documents/doc-a/links/{link.pk}/delete/')
        request.user = self.user
        response = document_link_delete(request, slug='doc-a', link_id=link.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(DocumentLink.objects.count(), 0)
