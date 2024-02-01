from django.db import models
 
class AudioFile(models.Model):
    audio_file = models.FileField(upload_to='audio_files/')
    id = models.AutoField(primary_key=True)
   

