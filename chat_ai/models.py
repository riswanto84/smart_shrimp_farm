from django.db import models
from django.contrib.auth.models import User
from ponds.models import Pond
class ChatSession(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE); pond=models.ForeignKey(Pond,on_delete=models.SET_NULL,null=True,blank=True); title=models.CharField(max_length=150, default='Chat AI Tambak'); created_at=models.DateTimeField(auto_now_add=True)
class ChatMessage(models.Model):
    session=models.ForeignKey(ChatSession,on_delete=models.CASCADE, related_name='messages'); role=models.CharField(max_length=20); message=models.TextField(); created_at=models.DateTimeField(auto_now_add=True)
