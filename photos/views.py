import json
import os
import uuid
import zipfile
from datetime import datetime
from io import BytesIO

import av
import boto3
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from PIL import Image

from photos.forms import FileForm

from .models import File


def countdown_page(request):
    naive = datetime.datetime.strptime(settings.WEDDING_DATE, "%Y-%m-%d %H:%M:%S")
    wedding_date = timezone.make_aware(naive).isoformat()
    return render(request, "countdown.html", {
        'wedding_date': wedding_date
    })


def login_token(request, token):
    user = authenticate(token=token)
    if user is not None:
        login(request, user, 'auth.backends.TokenBackEnd')
    return redirect('index')


@login_required
def index(request):
    return render(request, 'upload.html')


@login_required
def local_upload(request):
    if request.method == 'POST':
        form = FileForm(files=request.FILES)
        if form.is_valid():
            instance = form.save()
            if not settings.BUCKET_FILESTORE:
                if instance.is_image:
                    img = Image.open(instance.file)
                else:
                    container = av.open(instance.file)
                    for frame in container.decode(video=0):
                        img = frame.to_image()
                        break
                img = img.convert("RGB")
                img.thumbnail((300, 300))
                thumb_io = BytesIO()
                img.save(thumb_io, format='WEBP', quality=75)

                filename = os.path.splitext(os.path.basename(instance.file.name))[0]
                thumb_name = f"{filename}.webp"

                instance.thumbnail.save(
                    thumb_name,
                    ContentFile(thumb_io.getvalue()),
                    save=True
                )
            return JsonResponse({'status': 'ok'})
            


@login_required
def show_gallery(request):
    files = File.objects.all().order_by('-uploaded_at')
    if settings.BUCKET_FILESTORE:
        zip_url = f'https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/zips/gallery.zip'
    else:
        zip_url = f'{settings.MEDIA_URL}zips/gallery.zip'
    return render(request, 'gallery.html', {'files': files, 'zip_file_url': zip_url})


@login_required
def get_upload_url(request):
    if request.method == 'POST':
        file_name = request.POST.get('file_name')
        key = f'uploads/{uuid.uuid4()}_{file_name}'

        if settings.BUCKET_FILESTORE:
            bucket_name = settings.AWS_STORAGE_BUCKET_NAME
            s3 = boto3.client('s3',
                              aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                              aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                              region_name=settings.AWS_S3_REGION_NAME
                              )
            pload = s3.generate_presigned_post(Bucket=bucket_name,
                                               Key=key,
                                               ExpiresIn=500)
            public_url = f'https://{bucket_name}.s3.amazonaws.com/{key}'
            return JsonResponse({
                'pload': pload,
                'public_url': public_url,
                'key': key
            })
        else:
            return JsonResponse({
                'pload': {'url': '/local_upload/', 'fields': {}},
                'public_url': False
            })


@login_required
def save_file_url(request):
    """
        Method used in production
    """
    if request.method == 'POST':
        key = request.POST.get('key')
        filename = key.split('/')[-1]
        filename_no_ext = os.path.splitext(filename)[0]
        thumb_key = f"thumbnails/{filename_no_ext}.webp"

        file = File()
        file.file.name = key
        file.thumbnail.name = thumb_key
        file.save()

        return JsonResponse({'status': 'ok'})


@login_required
def download_selected_zip(request):
    if request.method == "POST":
        file_ids = request.POST.getlist("file_ids[]")
        files = File.objects.filter(id__in=file_ids)

        if settings.BUCKET_FILESTORE:
            # Production: delegate to Lambda, browser downloads directly from S3
            keys = [f.file.name for f in files]
            lambda_client = boto3.client(
                'lambda',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
            )
            response = lambda_client.invoke(
                FunctionName='generate-gallery-zip',
                InvocationType='RequestResponse',
                Payload=json.dumps({'keys': keys}),
            )
            result = json.loads(response['Payload'].read())
            return JsonResponse({'download_url': result['download_url']})
        else:
            # Local: build ZIP using storage API
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in files:
                    filename = f.file.name.split("/")[-1]
                    with default_storage.open(f.file.name, "rb") as file_data:
                        zf.writestr(filename, file_data.read())
            zip_buffer.seek(0)
            response = HttpResponse(
                zip_buffer,
                content_type="application/zip"
            )
            response["Content-Disposition"] = (
                'attachment; filename="selected_files.zip"'
            )
            return response

