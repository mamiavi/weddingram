import os
import io
import zipfile
from django.http import HttpResponse
from django.shortcuts import render, redirect
from .forms import PhotoForm
from .models import Photo
from django.contrib.auth.decorators import login_required

def index(request):
    return render(request, 'index.html')

@login_required
def upload_photo(request):
    if request.method == 'POST':
        images = request.FILES.getlist('image')
        for image in images:
            form = PhotoForm(files={'image': image})
            if form.is_valid():
                form.save()
        return redirect('gallery')
    else:
        form = PhotoForm()
    return render(request, 'upload.html', {'form': form})

@login_required
def show_gallery(request):
    photos = Photo.objects.all().order_by('-uploaded_at')
    return render(request, 'gallery.html', {'photos': photos})

@login_required
def download_gallery_zip(request):
    photos = Photo.objects.all()

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for photo in photos:
            file_path = photo.image.path
            file_name = os.path.basename(file_path)
            with open(file_path, 'rb') as f:
                zip_file.writestr(file_name, f.read())

    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="galeria.zip"'
    return response