from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path("countdown/", views.countdown_page, name="countdown"),
    path('local_upload/', views.local_upload, name='local_upload'),
    path('gallery/', views.show_gallery, name='gallery'),
    path('get_upload_url/', views.get_upload_url, name='get_url'),
    path('save_file_url/', views.save_file_url, name='save_url'),
    path('login_qr/<uuid:token>/', views.login_token, name='login_token'),
    path('download-selected/', views.download_selected_zip, name="download_selected")
]
