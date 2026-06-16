import hashlib

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import ApiKey


class BearerTokenAuthentication(BaseAuthentication):
    keyword = 'Bearer'

    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith(f'{self.keyword} '):
            return None

        raw_key = auth_header[len(self.keyword) + 1:].strip()
        if not raw_key:
            raise AuthenticationFailed('Пустой API-ключ.')

        api_key = ApiKey.authenticate(raw_key)
        if api_key is None:
            raise AuthenticationFailed('Недействительный API-ключ.')

        ApiKey.objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())
        return (api_key.created_by, api_key)

    def authenticate_header(self, request):
        return self.keyword
