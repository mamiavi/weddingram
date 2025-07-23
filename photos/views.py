import uuid

import boto3
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from photos.forms import FileForm

from .models import File


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