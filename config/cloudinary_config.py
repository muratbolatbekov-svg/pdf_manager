import os
from urllib.parse import unquote, urlparse


def _is_valid(credentials):
    return bool(
        credentials
        and credentials.get('CLOUD_NAME')
        and credentials.get('API_KEY')
        and credentials.get('API_SECRET')
    )


def _from_env_vars():
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME', '').strip()
    api_key = os.environ.get('CLOUDINARY_API_KEY', '').strip()
    api_secret = os.environ.get('CLOUDINARY_API_SECRET', '').strip()
    if cloud_name and api_key and api_secret:
        return {
            'CLOUD_NAME': cloud_name,
            'API_KEY': api_key,
            'API_SECRET': api_secret,
        }
    return None


def _from_url():
    url = os.environ.get('CLOUDINARY_URL', '').strip()
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
