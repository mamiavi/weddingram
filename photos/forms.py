from django import forms
from .models import Photo

class PhotoForm(forms.ModelForm):
    class Meta:
        model = Photo
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={'accept': 'image/*', 'capture':'camera'})
            }