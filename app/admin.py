from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import  AudioFile,UserDetail

admin.site.register(AudioFile)
admin.site.register(UserDetail)
