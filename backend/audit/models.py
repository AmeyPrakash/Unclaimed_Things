import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone

class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_actions'
    )
    action = models.CharField(max_length=100, db_index=True)
    entity_type = models.CharField(max_length=50, db_index=True)
    entity_id = models.CharField(max_length=100, db_index=True)
    request_id = models.CharField(max_length=100, blank=True, db_index=True)
    metadata_redacted = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'utn_audit_events'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.action}] {self.entity_type}:{self.entity_id} by {self.actor} at {self.created_at}"
