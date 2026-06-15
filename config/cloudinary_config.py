import os
from urllib.parse import unquote, urlparse


def _clean(value):
    if not value:
        return ''
    return value.strip().strip('"').strip("'")


def _is_valid(credentials):
    return bool(
        credentials
        and credentials.get('CLOUD_NAME')
        and credentials.get('API_KEY')
        and credentials.get('API_SECRET')
    )


def _from_env_vars():
    cloud_name = _clean(os.environ.get('CLOUDINARY_CLOUD_NAME'))
    api_key = _clean(os.environ.get('CLOUDINARY_API_KEY'))
    api_secret = _clean(os.environ.get('CLOUDINARY_API_SECRET'))
    if cloud_name and api_key and api_secret:
        return {
            'CLOUD_NAME': cloud_name,
            'API_KEY': api_key,
            'API_SECRET': api_secret,
        }
    return None


def _from_url():
    url = _clean(os.environ.get('CLOUDINARY_URL'))
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme != 'cloudinary' or not parsed.hostname:
        return None
    credentials = {
        'CLOUD_NAME': parsed.hostname,
        'API_KEY': unquote(parsed.username or ''),
        'API_SECRET': unquote(parsed.password or ''),
    }
    return credentials if _is_valid(credentials) else None


def has_partial_cloudinary_env():
    values = [
        _clean(os.environ.get('CLOUDINARY_CLOUD_NAME')),
        _clean(os.environ.get('CLOUDINARY_API_KEY')),
        _clean(os.environ.get('CLOUDINARY_API_SECRET')),
        _clean(os.environ.get('CLOUDINARY_URL')),
    ]
    return any(values) and not load_cloudinary_credentials()


def missing_cloudinary_env_keys():
    missing = []
    if not _clean(os.environ.get('CLOUDINARY_CLOUD_NAME')):
        missing.append('CLOUDINARY_CLOUD_NAME')
    if not _clean(os.environ.get('CLOUDINARY_API_KEY')):
        missing.append('CLOUDINARY_API_KEY')
    if not _clean(os.environ.get('CLOUDINARY_API_SECRET')):
        missing.append('CLOUDINARY_API_SECRET')
    return missing


def load_cloudinary_credentials():
    """Prefer individual env vars over CLOUDINARY_URL."""
    for loader in (_from_env_vars, _from_url):
        credentials = loader()
        if _is_valid(credentials):
            return credentials
    return None


def dev_cloudinary_credentials():
    return {
        'CLOUD_NAME': 'dpevynhal',
        'API_KEY': '779224643712774',
        'API_SECRET': '3hRHtDQ7FDjY91_99PVd7fPhNMQ',
    }
