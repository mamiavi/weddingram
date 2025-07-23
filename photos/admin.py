from django.contrib import admin
from django.utils.html import format_html

from .models import File


class FileAdmin(admin.ModelAdmin):

    def media_tag(self, obj):
        if obj.is_image():
            return format_html('<img src="{}" style="max-width:200px; max-height:200px"/>'.format(obj.file.url))
        elif obj.is_video():
            return format_html('<video src="{}" width="50" height="50" controls></video>'.format(obj.file.url))
    list_display = ['media_tag', 'file']


admin.site.register(File, FileAdmin)
