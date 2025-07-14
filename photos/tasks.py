import io
import os
import zipfile

from celery import shared_task
from django.core.files.storage import default_storage
from photos.models import Photo


@shared_task
def create_gallery_zip_task():
    photos = Photo.objects.all()

    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for photo in photos:
            file_name = os.path.basename(photo.file.name)
            with photo.file.open('rb') as f:
                zip_file.writestr(file_name, f.read())

    zip_buffer.seek(0)

    # Upload ZIP to storage (S3 or local)
    zip_path = f'zips/gallery.zip'
    default_storage.save(zip_path, zip_buffer)

    return zip_path

