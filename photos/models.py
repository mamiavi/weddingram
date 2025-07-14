from django.db import models
from django.utils.html import mark_safe

class Photo(models.Model):
    file = models.ImageField(upload_to='uploads/', max_length=500)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def image_tag(self):
        return mark_safe('<img src="%s" width ="50" height="50"/>'%(self.file.url))
