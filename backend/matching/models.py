import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from reports.models import ItemReport

class FeedbackType(models.TextChoices):
    RELEVANT = 'RELEVANT', 'Relevant'
    NOT_RELEVANT = 'NOT_RELEVANT', 'Not Relevant'
    CLAIMED = 'CLAIMED', 'Claimed'
    RECOVERED = 'RECOVERED', 'Recovered'

class MatchFeedback(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    query_report = models.ForeignKey(
        ItemReport,
        on_delete=models.CASCADE,
        related_name='feedback_given'
    )
    candidate_report = models.ForeignKey(
        ItemReport,
        on_delete=models.CASCADE,
        related_name='feedback_received'
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    feedback = models.CharField(max_length=20, choices=FeedbackType.choices)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'utn_match_feedbacks'
        ordering = ['-created_at']

    def __str__(self):
        return f"Feedback {self.feedback} by {self.actor} for {self.candidate_report_id}"
