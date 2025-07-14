from django.contrib import admin
from django.utils.html import format_html
from .models import Photo

class PhotoAdmin(admin.ModelAdmin):

    def image_tag(self, obj):
        return format_html('<img src="{}" style="max-width:200px; max-height:200px"/>'.format(obj.file.url))

    list_display = ['image_tag', 'file']

admin.site.register(Photo, PhotoAdmin)
