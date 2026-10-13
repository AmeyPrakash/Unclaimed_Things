import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from reports.models import ItemReport
from locations.models import Location

class CustodyEventType(models.TextChoices):
    REGISTERED = 'REGISTERED', 'Registered'
    TRANSFER_REQUESTED = 'TRANSFER_REQUESTED', 'Transfer Requested'
    TRANSFER_ACCEPTED = 'TRANSFER_ACCEPTED', 'Transfer Accepted'
    HANDOVER_COMPLETED = 'HANDOVER_COMPLETED', 'Handover Completed'
    CORRECTION = 'CORRECTION', 'Correction'

class CustodyEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(
        ItemReport,
        on_delete=models.CASCADE,
        related_name='custody_events'
    )
    event_type = models.CharField(
        max_length=30,
        choices=CustodyEventType.choices
    )
    from_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='custody_transfers_from'
    )
    to_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='custody_transfers_to'
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    related_event = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='related_corrections'
    )
    note_private = models.TextField(blank=True, null=True)
    occurred_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'utn_custody_events'
        ordering = ['occurred_at']

    def __str__(self):
        return f"[{self.event_type}] Report {self.report_id} by {self.actor}"
