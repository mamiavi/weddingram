import os
import zipfile
import boto3
from django.core.management.base import BaseCommand
from django.conf import settings
from photos.models import File


class Command(BaseCommand):
    help = 'Generates a ZIP of all uploaded files and uploads it to S3'

    def handle(self, *args, **kwargs):
        self.stdout.write('Fetching file list...')
        files = File.objects.all()

        s3 = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        tmp_zip_path = '/tmp/gallery.zip'

        self.stdout.write(f'Zipping {files.count()} files...')
        with zipfile.ZipFile(tmp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                self.stdout.write(f'Adding {f.file.name}...')
                obj = s3.get_object(Bucket=bucket, Key=f.file.name)
                filename = f.file.name.split('/')[-1]
                with zf.open(filename, 'w') as zf_file:
                    for chunk in obj['Body'].iter_chunks(chunk_size=1024*1024):
                        zf_file.write(chunk)

        self.stdout.write('Uploading ZIP to S3...')
        s3.upload_file(tmp_zip_path, bucket, 'zips/gallery.zip')
        os.remove(tmp_zip_path)
        self.stdout.write(self.style.SUCCESS('Done! gallery.zip uploaded to S3.'))