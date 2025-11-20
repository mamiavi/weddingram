import io
import os
import zipfile

from celery import shared_task
from django.core.files.storage import default_storage

from photos.models import File


@shared_task
def create_gallery_zip_task():
    files = File.objects.all()

    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file in files:
            file_name = os.path.basename(file.file.name)
            with file.file.open('rb') as f:
                zip_file.writestr(file_name, f.read())

    zip_buffer.seek(0)

    # Upload ZIP to storage (S3 or local)
    zip_path = 'zips/gallery.zip'
    default_storage.save(zip_path, zip_buffer)

    return zip_path

