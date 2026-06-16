import os
import re


def _clean(value):
    if not value:
        return ''
    return value.strip().strip('"').strip("'")


B2_ENV_KEYS = ('B2_KEY_ID', 'B2_APPLICATION_KEY', 'B2_BUCKET_NAME', 'B2_ENDPOINT')


def _region_from_endpoint(endpoint):
    match = re.search(r'\.(us-east-\d+|us-west-\d+|eu-central-\d+)\.', endpoint)
    return match.group(1) if match else 'us-east-005'


def load_b2_credentials():
    key_id = _clean(os.environ.get('B2_KEY_ID'))
    application_key = _clean(os.environ.get('B2_APPLICATION_KEY'))
    bucket_name = _clean(os.environ.get('B2_BUCKET_NAME'))
    endpoint = _clean(os.environ.get('B2_ENDPOINT'))
    if not (key_id and application_key and bucket_name and endpoint):
        return None
    endpoint = endpoint.removeprefix('https://').removeprefix('http://')
    region = _clean(os.environ.get('B2_REGION')) or _region_from_endpoint(endpoint)
    return {
        'KEY_ID': key_id,
        'APPLICATION_KEY': application_key,
        'BUCKET_NAME': bucket_name,
        'ENDPOINT': endpoint,
        'REGION': region,
    }


def has_partial_b2_env():
    values = [_clean(os.environ.get(key)) for key in B2_ENV_KEYS]
    return any(values) and not load_b2_credentials()


def missing_b2_env_keys():
    missing = []
    for key in B2_ENV_KEYS:
        if not _clean(os.environ.get(key)):
            missing.append(key)
    return missing
