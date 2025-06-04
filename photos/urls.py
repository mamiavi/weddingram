from django.urls import path

from . import views

urlpatterns = [
    path('', views.upload_photo, name='upload'),
    path('gallery/', views.show_gallery, name='gallery'),
    path('gallery/download/', views.download_gallery_zip, name='download_gallery'),
]
