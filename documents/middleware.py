from django.conf import settings
from django.utils import translation
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import check_for_language
from django.views.i18n import set_language as django_set_language

SESSION_LANGUAGE_KEY = 'django_language'


class SessionLanguageMiddleware(MiddlewareMixin):
    """Apply language stored in the user session (after LocaleMiddleware)."""

    def process_request(self, request):
        if not hasattr(request, 'session'):
            return
        lang = request.session.get(SESSION_LANGUAGE_KEY)
        if lang and check_for_language(lang):
            translation.activate(lang)
            request.LANGUAGE_CODE = translation.get_language()


def set_language(request):
    response = django_set_language(request)
    if request.method == 'POST':
        lang_code = request.POST.get('language')
        if lang_code and check_for_language(lang_code):
            request.session[SESSION_LANGUAGE_KEY] = lang_code
    return response
