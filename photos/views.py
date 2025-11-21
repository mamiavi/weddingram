import os
import uuid

import boto3
import zipstream
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.http import Http404, JsonResponse, StreamingHttpResponse
from django.shortcuts import redirect, render

from photos.forms import FileForm

from .models import File


def countdown_page(request):
    return render(request, "countdown.html")


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
            form.save()
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
    if request.method == 'POST':
        key = request.POST.get('key')
        file = File()
        file.file.name = key
        file.save()
        return JsonResponse({'status': 'ok'})


@login_required
def download_selected_zip(request):
    if request.method == "POST":
        file_ids = request.POST.getlist("file_ids[]")
        files = File.objects.filter(id__in=file_ids)

        zip_stream = zipstream.ZipFile(mode="w", compression=zipstream.ZIP_DEFLATED)

        for f in files:
            filename = os.path.basename(f.file.name)
            file_obj = default_storage.open(f.file.name, "rb")

            # Wrap in iterator to stream in chunks
            zip_stream.write_iter(
                filename, 
                iter(lambda file_obj=file_obj: file_obj.read(1024*64), b"")
            )

        response = StreamingHttpResponse(
            zip_stream, content_type="application/zip"
        )
        response['Content-Disposition'] = 'attachment; filename="selected_files.zip"'

        return response

