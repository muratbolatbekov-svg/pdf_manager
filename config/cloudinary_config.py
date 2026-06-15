import os
from urllib.parse import unquote, urlparse


def load_cloudinary_credentials():
    """Load Cloudinary credentials from CLOUDINARY_URL or individual env vars."""
    url = os.environ.get('CLOUDINARY_URL', '').strip()
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME', '').strip()
    api_key = os.environ.get('CLOUDINARY_API_KEY', '').strip()
    api_secret = os.environ.get('CLOUDINARY_API_SECRET', '').strip()

    if url:
        parsed = urlparse(url)
        if parsed.scheme == 'cloudinary' and parsed.hostname:
            return {
                'CLOUD_NAME': parsed.hostname,
                'API_KEY': unquote(parsed.username or '') or api_key,
                'API_SECRET': unquote(parsed.password or '') or api_secret,
            }

    if cloud_name and api_key and api_secret:
        return {
            'CLOUD_NAME': cloud_name,
            'API_KEY': api_key,
            'API_SECRET': api_secret,
        }

    return None


def dev_cloudinary_credentials():
    return {
        'CLOUD_NAME': 'dpevynhal',
        'API_KEY': '779224643712774',
        'API_SECRET': '3hRHtDQ7FDjY91_99PVd7fPhNMQ',
    }
