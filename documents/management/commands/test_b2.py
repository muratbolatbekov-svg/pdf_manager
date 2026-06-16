import io

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Проверяет подключение к Backblaze B2'

    def handle(self, *args, **options):
        credentials = getattr(settings, 'B2_CREDENTIALS', None)
        if not credentials:
            self.stdout.write(self.style.ERROR('B2 credentials are not configured.'))
            return

        import boto3
        from botocore.exceptions import ClientError

        self.stdout.write(
            f"Bucket: {credentials['BUCKET_NAME']}\n"
            f"Endpoint: https://{credentials['ENDPOINT']}\n"
            f"Region: {credentials['REGION']}"
        )

        client = boto3.client(
            's3',
            endpoint_url=f"https://{credentials['ENDPOINT']}",
            aws_access_key_id=credentials['KEY_ID'],
            aws_secret_access_key=credentials['APPLICATION_KEY'],
            region_name=credentials['REGION'],
        )

        try:
            client.head_bucket(Bucket=credentials['BUCKET_NAME'])
            self.stdout.write(self.style.SUCCESS('B2 bucket access OK'))
        except ClientError as exc:
            self.stdout.write(self.style.ERROR(f'B2 bucket access error: {exc}'))
            return

        test_key = '_healthcheck/test.pdf'
        test_content = b'%PDF-1.4 test'
        try:
            client.put_object(
                Bucket=credentials['BUCKET_NAME'],
                Key=test_key,
                Body=io.BytesIO(test_content),
                ContentType='application/pdf',
            )
            self.stdout.write(self.style.SUCCESS('B2 upload OK'))
            client.delete_object(Bucket=credentials['BUCKET_NAME'], Key=test_key)
            self.stdout.write(self.style.SUCCESS('B2 delete OK'))
        except ClientError as exc:
            self.stdout.write(self.style.ERROR(f'B2 upload/delete error: {exc}'))
