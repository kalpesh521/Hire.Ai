from django.db import models
from .choices import ROLE_CHOICES, EXP_CHOICES,SKILLS_CHOICES
import uuid
class AudioFile(models.Model):
    audio_file = models.FileField(upload_to='audio_files/')
    id = models.AutoField(primary_key=True)
   
class UserDetail(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(choices=ROLE_CHOICES, max_length=100)  
    experience = models.CharField(choices=EXP_CHOICES, max_length=100)  
    skills = models.CharField(choices=SKILLS_CHOICES, max_length=100)  

    def __str__(self):
        return str(self.id)
