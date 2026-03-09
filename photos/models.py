from django.contrib.auth.models import User
from django.db import models
from django.templatetags.static import static
from django.utils.html import mark_safe

VIDEO_FORMATS = ('.mp4', '.mov', '.avi', '.webm')
IMAGE_FORMATS = ('.jpg', '.jpeg', '.png', '.webp', '.gif')


class File(models.Model):
    file = models.FileField(upload_to='uploads/', max_length=500)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    thumbnail = models.FileField(upload_to='thumbnails/', max_length=500, blank=True, null=True)

    @property
    def is_video(self):
        return self.file.name.lower().endswith(VIDEO_FORMATS)

    @property
    def is_image(self):
        return self.file.name.lower().endswith(IMAGE_FORMATS)

    def media_tag(self):
        if self.is_video():
            return mark_safe(f'<video src="{self.file.url}" width="50" height="50" controls></>')
        return mark_safe(f'<img src="{self.file.url}" width="50" height="50" />')

    @property
    def thumbnail_url(self):
        if self.thumbnail and self.thumbnail.name:
            return self.thumbnail.url
        if self.is_image:
            return static('img/img_thumbnail.jpg')
        else:
            return static('img/video_thumbnail.png')


class Token(models.Model):
    uuid = models.UUIDField(unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
