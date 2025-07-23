from django.db import models
from django.utils.html import mark_safe

VIDEO_FORMATS = ('.mp4', '.mov', '.avi', '.webm')
IMAGE_FORMATS = ('.jpg', '.jpeg', '.png', '.webp', '.gif')


class File(models.Model):
    file = models.FileField(upload_to='uploads/', max_length=500)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def is_video(self):
        return self.file.name.lower().endswith(VIDEO_FORMATS)

    def is_image(self):
        return self.file.name.lower().endswith(IMAGE_FORMATS)

    def media_tag(self):
        if self.is_video():
            return mark_safe(f'<video src="{self.file.url}" width="50" height="50" controls></video>')
        return mark_safe(f'<img src="{self.file.url}" width="50" height="50" />')