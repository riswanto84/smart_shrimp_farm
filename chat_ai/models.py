from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from ponds.models import Pond
from cultivation.models import CultivationCycle


class ChatSession(models.Model):
    RETENTION_IMPORTANT = 'important'
    RETENTION_NORMAL = 'normal'
    RETENTION_ERROR = 'error'
    RETENTION_CHOICES = [
        (RETENTION_IMPORTANT, 'Penting / Simpan Permanen'),
        (RETENTION_NORMAL, 'Biasa / Simpan 6 Bulan'),
        (RETENTION_ERROR, 'Gagal / Simpan 30 Hari'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cycle = models.ForeignKey(CultivationCycle, on_delete=models.PROTECT, null=True, blank=True, related_name='chat_sessions')
    pond = models.ForeignKey(Pond, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=150, default='Percakapan Baru')
    model_name = models.CharField(max_length=100, blank=True)
    retention_type = models.CharField(max_length=20, choices=RETENTION_CHOICES, default=RETENTION_NORMAL)
    is_important = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def expires_at(self):
        if self.retention_type == self.RETENTION_IMPORTANT or self.is_important:
            return None
        if self.retention_type == self.RETENTION_ERROR:
            return self.created_at + timedelta(days=30)
        return self.created_at + timedelta(days=180)

    def __str__(self):
        return self.title or f'Chat AI Tambak #{self.id}'


class ChatMessage(models.Model):
    ROLE_CHOICES = [('user', 'User'), ('assistant', 'Assistant'), ('system', 'System')]
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    message = models.TextField(blank=True)
    context_snapshot = models.JSONField(null=True, blank=True)
    is_complete = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.role}: {self.message[:50]}'


class ChatAttachment(models.Model):
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='chat_ai/%Y/%m/%d/')
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120, blank=True)
    size = models.PositiveBigIntegerField(default=0)
    extracted_text = models.TextField(blank=True)
    extraction_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def extension(self):
        return Path(self.original_name).suffix.lower()

    def __str__(self):
        return self.original_name
