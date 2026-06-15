import os

import cloudinary.uploader
from cloudinary_storage.storage import MediaCloudinaryStorage
from django.conf import settings


class PdfCloudinaryStorage(MediaCloudinaryStorage):
    """Upload PDFs with resource_type=auto and optional unsigned upload preset."""

    RESOURCE_TYPE = 'raw'

    def _upload_resource_type(self):
        return getattr(settings, 'CLOUDINARY_UPLOAD_RESOURCE_TYPE', 'auto')

    def _upload(self, name, content):
        options = {
            'use_filename': True,
            'resource_type': self._upload_resource_type(),
            'tags': self.TAG,
        }
        folder = os.path.dirname(name)
        if folder:
            options['folder'] = folder

        upload_preset = getattr(settings, 'CLOUDINARY_UPLOAD_PRESET', None)
        if upload_preset:
            options['upload_preset'] = upload_preset

        return cloudinary.uploader.upload(content, **options)

    def delete(self, name):
        for resource_type in ('raw', 'image', 'video'):
            response = cloudinary.uploader.destroy(
                name,
                invalidate=True,
                resource_type=resource_type,
            )
            if response.get('result') == 'ok':
                return True
        return False
