from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('local_upload/', views.local_upload, name='local_upload'),
    path('gallery/', views.show_gallery, name='gallery'),
    path('get_upload_url/', views.get_upload_url, name='get_url'),
    path('save_img_url/', views.save_img_url, name='save_url')
]
