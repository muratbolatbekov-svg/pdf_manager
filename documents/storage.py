from storages.backends.s3boto3 import S3Boto3Storage


class PdfB2Storage(S3Boto3Storage):
    """Store PDF files in Backblaze B2 via the S3-compatible API."""

    file_overwrite = False
