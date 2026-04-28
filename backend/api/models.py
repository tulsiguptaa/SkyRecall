# backend/api/models.py
from django.db import models
from django.contrib.auth.models import User

class UserMedia(models.Model):
    MEDIA_TYPES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='media')
    file = models.FileField(upload_to='user_media/%Y/%m/%d/')
    media_type = models.CharField(max_length=5, choices=MEDIA_TYPES)
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Detection results
    objects_detected = models.JSONField(default=list)
    tags = models.JSONField(default=list)
    faces_detected = models.JSONField(default=dict)
    labels = models.JSONField(default=list)
    
    thumbnail = models.ImageField(upload_to='thumbnails/', null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.file_name}"
    
    class Meta:
        ordering = ['-uploaded_at']