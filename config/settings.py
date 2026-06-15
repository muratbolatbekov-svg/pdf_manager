from pathlib import Path
import os

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from config.cloudinary_config import dev_cloudinary_credentials, load_cloudinary_credentials

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get('DEBUG', 'True') == 'True'
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-dev-only-change-in-production'
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
    'cloudinary_storage',
    'cloudinary',
    'documents.apps.DocumentsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
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

CLOUDINARY_CREDENTIALS = load_cloudinary_credentials()
if not CLOUDINARY_CREDENTIALS:
    if DEBUG:
        CLOUDINARY_CREDENTIALS = dev_cloudinary_credentials()
    else:
        raise ImproperlyConfigured(
            'Cloudinary credentials are required. Set CLOUDINARY_URL or '
            'CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET.'
        )

import cloudinary

cloudinary.config(
    cloud_name=CLOUDINARY_CREDENTIALS['CLOUD_NAME'],
    api_key=CLOUDINARY_CREDENTIALS['API_KEY'],
    api_secret=CLOUDINARY_CREDENTIALS['API_SECRET'],
    secure=True,
)

CLOUDINARY = {
    'cloud_name': CLOUDINARY_CREDENTIALS['CLOUD_NAME'],
    'api_key': CLOUDINARY_CREDENTIALS['API_KEY'],
    'api_secret': CLOUDINARY_CREDENTIALS['API_SECRET'],
    'secure': True,
}

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': CLOUDINARY_CREDENTIALS['CLOUD_NAME'],
    'API_KEY': CLOUDINARY_CREDENTIALS['API_KEY'],
    'API_SECRET': CLOUDINARY_CREDENTIALS['API_SECRET'],
    'SECURE': True,
}

STORAGES = {
    'default': {
        'BACKEND': 'cloudinary_storage.storage.RawMediaCloudinaryStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

MEDIA_URL = '/media/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Asia/Almaty'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

PDF_MAX_SIZE = 10 * 1024 * 1024
CONTRACT_EXPIRY_WARNING_DAYS = int(os.environ.get('CONTRACT_EXPIRY_WARNING_DAYS', '30'))

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
}

EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@pdf-database.local')
NOTIFY_EMAIL = os.environ.get('NOTIFY_EMAIL', '')

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
