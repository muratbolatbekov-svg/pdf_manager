from pathlib import Path
import os

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

_env_file = BASE_DIR / '.env'
if _env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_file)
    except ImportError:
        pass

from config.b2_config import (
    has_partial_b2_env,
    load_b2_credentials,
    missing_b2_env_keys,
)

DEBUG = os.environ.get('DEBUG', 'True') == 'True'
ON_RAILWAY = bool(os.environ.get('RAILWAY_ENVIRONMENT'))

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-dev-only-change-in-production'
    elif ON_RAILWAY:
        SECRET_KEY = 'django-insecure-set-secret-key-in-railway-variables'
    else:
        raise ImproperlyConfigured('SECRET_KEY environment variable is required in production.')

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        'CSRF_TRUSTED_ORIGINS',
        'https://pdfmanager-production-bf1d.up.railway.app',
    ).split(',')
    if origin.strip()
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_spectacular',
    'storages',
    'documents.apps.DocumentsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'documents.middleware.SessionLanguageMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
            'django.template.context_processors.i18n',
            'documents.context_processors.user_role',
        ],
    },
}]
WSGI_APPLICATION = 'config.wsgi.application'

DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

B2_CREDENTIALS = load_b2_credentials()
MEDIA_URL = '/media/'

if B2_CREDENTIALS:
    AWS_ACCESS_KEY_ID = B2_CREDENTIALS['KEY_ID']
    AWS_SECRET_ACCESS_KEY = B2_CREDENTIALS['APPLICATION_KEY']
    AWS_STORAGE_BUCKET_NAME = B2_CREDENTIALS['BUCKET_NAME']
    AWS_S3_ENDPOINT_URL = f"https://{B2_CREDENTIALS['ENDPOINT']}"
    AWS_S3_REGION_NAME = B2_CREDENTIALS['REGION']
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_DEFAULT_ACL = None
    AWS_S3_ADDRESSING_STYLE = 'virtual'
    AWS_QUERYSTRING_AUTH = os.environ.get('B2_QUERYSTRING_AUTH', 'True') == 'True'
    AWS_QUERYSTRING_EXPIRE = int(os.environ.get('B2_URL_EXPIRE', '604800'))
    AWS_S3_FILE_OVERWRITE = False
    DEFAULT_FILE_STORAGE = 'documents.storage.PdfB2Storage'
elif has_partial_b2_env():
    missing = ', '.join(missing_b2_env_keys())
    raise ImproperlyConfigured(
        f'Backblaze B2 credentials incomplete. Missing or empty: {missing}. '
        'Set B2_KEY_ID, B2_APPLICATION_KEY, B2_BUCKET_NAME and B2_ENDPOINT.'
    )
elif DEBUG and not ON_RAILWAY:
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_ROOT = BASE_DIR / 'media'
else:
    raise ImproperlyConfigured(
        'Backblaze B2 credentials are required. Set B2_KEY_ID, B2_APPLICATION_KEY, '
        'B2_BUCKET_NAME and B2_ENDPOINT in environment variables.'
    )

STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

LANGUAGE_CODE = 'ru'
TIME_ZONE = 'Asia/Almaty'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ('ru', 'Русский'),
    ('kk', 'Қазақша'),
    ('en', 'English'),
]

LOCALE_PATHS = [BASE_DIR / 'locale']

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

PDF_MAX_SIZE = 10 * 1024 * 1024
CONTRACT_EXPIRY_WARNING_DAYS = int(os.environ.get('CONTRACT_EXPIRY_WARNING_DAYS', '30'))

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'documents.api_auth.BearerTokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'PDF Data Base API',
    'DESCRIPTION': 'REST API для управления документами PDF Data Base. Аутентификация: Authorization: Bearer sk-...',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SECURITY': [{'BearerAuth': []}],
}

EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@pdf-database.local')
NOTIFY_EMAIL = os.environ.get('NOTIFY_EMAIL', '')
APP_URL = os.environ.get('APP_URL', '').strip()
if not APP_URL and CSRF_TRUSTED_ORIGINS:
    APP_URL = CSRF_TRUSTED_ORIGINS[0]
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
