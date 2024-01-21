from django.db import models


class AudioFile(models.Model):
    audio_file = models.FileField(upload_to='audio_files/')
    id = models.AutoField(primary_key=True)
     
    
class Interview(models.Model):
    prompt = models.TextField()
    transcript = models.TextField(blank=True, null=True)
    audio_file = models.FileField(upload_to='audio_files/', blank=True, null=True)

    def __str__(self):
        return f"Interview {self.id}"

