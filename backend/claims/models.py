import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from reports.models import ItemReport

class ClaimStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    NEEDS_INFO = 'NEEDS_INFO', 'Needs Info'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    CANCELLED = 'CANCELLED', 'Cancelled'
    COMPLETED = 'COMPLETED', 'Completed'

class Claim(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(
        ItemReport,
        on_delete=models.CASCADE,
        related_name='claims'
    )
    claimant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='claims'
    )
    status = models.CharField(
        max_length=20,
        choices=ClaimStatus.choices,
        default=ClaimStatus.PENDING
    )
    claimant_statement = models.TextField(
        help_text="Private statement from claimant explaining proof of ownership"
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='claims_reviewed'
    )
    review_note_private = models.TextField(blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'utn_claims'
        ordering = ['-created_at']

    def __str__(self):
        return f"Claim {self.id} for report {self.report_id} [{self.status}]"

class EvidenceType(models.TextChoices):
    TEXT = 'TEXT', 'Text'
    IMAGE = 'IMAGE', 'Image'
    OTHER = 'OTHER', 'Other'

class ClaimEvidence(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claim = models.ForeignKey(
        Claim,
        on_delete=models.CASCADE,
        related_name='evidences'
    )
    evidence_type = models.CharField(
        max_length=15,
        choices=EvidenceType.choices,
        default=EvidenceType.TEXT
    )
    private_value = models.TextField(
        help_text="Private text detail or secure object storage key"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'utn_claim_evidences'

    def __str__(self):
        return f"Evidence {self.id} for claim {self.claim_id}"
