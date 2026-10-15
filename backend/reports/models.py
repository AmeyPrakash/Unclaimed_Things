import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from pgvector.django import VectorField
from locations.models import Location

class ReportType(models.TextChoices):
    LOST = 'LOST', 'Lost'
    FOUND = 'FOUND', 'Found'

class ItemCategory(models.TextChoices):
    ELECTRONICS = 'ELECTRONICS', 'Electronics'
    BAG = 'BAG', 'Bag'
    CLOTHING = 'CLOTHING', 'Clothing'
    DOCUMENT = 'DOCUMENT', 'Document'
    ACCESSORY = 'ACCESSORY', 'Accessory'
    KEYS = 'KEYS', 'Keys'
    BOTTLE = 'BOTTLE', 'Bottle'
    OTHER = 'OTHER', 'Other'

class ReportStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    WITHDRAWN = 'WITHDRAWN', 'Withdrawn'
    EXPIRED = 'EXPIRED', 'Expired'
    RETURNED = 'RETURNED', 'Returned'

class ReportVisibility(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    HIDDEN = 'HIDDEN', 'Hidden'
    REMOVED = 'REMOVED', 'Removed'

class ItemReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report_type = models.CharField(max_length=10, choices=ReportType.choices)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports'
    )
    
    category = models.CharField(max_length=30, choices=ItemCategory.choices)
    title = models.CharField(max_length=200, help_text="Short descriptive title of the item")
    public_description = models.TextField(help_text="Safe public description without secret verification details")
    
    last_seen_at = models.DateTimeField(null=True, blank=True)
    found_at = models.DateTimeField(null=True, blank=True)
    
    last_seen_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lost_reports_seen_here'
    )
    found_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='found_reports_found_here'
    )
    current_holding_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='holding_items'
    )
    
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.OPEN
    )
    visibility = models.CharField(
        max_length=20,
        choices=ReportVisibility.choices,
        default=ReportVisibility.ACTIVE
    )
    
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'utn_item_reports'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['report_type', 'status', 'visibility']),
            models.Index(fields=['category', 'created_at']),
        ]

    def __str__(self):
        return f"[{self.report_type}] {self.title} ({self.status})"

class ReportPrivateDetail(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.OneToOneField(
        ItemReport,
        on_delete=models.CASCADE,
        related_name='private_detail'
    )
    private_description = models.TextField(
        blank=True,
        help_text="Private details, serial numbers, markings kept hidden from public view"
    )
    distinguishing_details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured private attributes (e.g. {'serial_number': '...', 'secret_sticker': '...'}"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'utn_report_private_details'

    def __str__(self):
        return f"Private details for {self.report_id}"

class ImageModerationStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'

class ReportImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(
        ItemReport,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image_file = models.ImageField(upload_to='reports/%Y/%m/%d/')
    storage_key = models.CharField(max_length=500, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    size_bytes = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    moderation_status = models.CharField(
        max_length=20,
        choices=ImageModerationStatus.choices,
        default=ImageModerationStatus.APPROVED
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'utn_report_images'

    def __str__(self):
        return f"Image for {self.report_id} ({self.moderation_status})"

class EmbeddingStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    READY = 'READY', 'Ready'
    FAILED = 'FAILED', 'Failed'

class ItemEmbedding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.OneToOneField(
        ItemReport,
        on_delete=models.CASCADE,
        related_name='embedding_record'
    )
    model_name = models.CharField(max_length=150, default='nvidia/nemotron-3-embed-1b')
    model_version = models.CharField(max_length=50, blank=True, null=True)
    embedding = VectorField(dimensions=2048, null=True, blank=True)
    embedding_status = models.CharField(
        max_length=20,
        choices=EmbeddingStatus.choices,
        default=EmbeddingStatus.PENDING
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'utn_item_embeddings'

    def __str__(self):
        return f"Embedding for {self.report_id} [{self.embedding_status}]"

class AbuseReason(models.TextChoices):
    SPAM_OR_FRAUD = 'SPAM_OR_FRAUD', 'Spam or Fraudulent Listing'
    INAPPROPRIATE = 'INAPPROPRIATE', 'Inappropriate or Offensive Content'
    PRIVATE_INFO_LEAK = 'PRIVATE_INFO_LEAK', 'Personal Contact or Private Info Leak'
    SUSPICIOUS_CLAIM = 'SUSPICIOUS_CLAIM', 'Suspicious Details / False Match'
    OTHER = 'OTHER', 'Other Abuse / Safety Concern'

class ReportAbuseFlag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(
        ItemReport,
        on_delete=models.CASCADE,
        related_name='abuse_flags'
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reported_flags'
    )
    reason = models.CharField(max_length=50, choices=AbuseReason.choices)
    details = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'utn_report_abuse_flags'
        unique_together = ('report', 'reporter')
        ordering = ['-created_at']

    def __str__(self):
        return f"Flag on {self.report_id} by {self.reporter_id} ({self.reason})"

