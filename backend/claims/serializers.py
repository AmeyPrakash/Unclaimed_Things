from rest_framework import serializers
from .models import Claim, ClaimEvidence, ClaimStatus

class ClaimEvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClaimEvidence
        fields = ['id', 'evidence_type', 'private_value', 'created_at', 'reviewed_at']
        read_only_fields = ['id', 'created_at', 'reviewed_at']

class ClaimSerializer(serializers.ModelSerializer):
    evidences = ClaimEvidenceSerializer(many=True, read_only=True)
    report_title = serializers.CharField(source='report.title', read_only=True)
    claimant_email = serializers.CharField(source='claimant.email', read_only=True)

    class Meta:
        model = Claim
        fields = [
            'id', 'report', 'report_title', 'claimant', 'claimant_email',
            'status', 'claimant_statement', 'reviewed_by',
            'review_note_private', 'decision_at', 'created_at', 'evidences'
        ]
        read_only_fields = ['id', 'claimant', 'status', 'reviewed_by', 'decision_at', 'created_at']

class ClaimCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Claim
        fields = ['id', 'report', 'claimant_statement']
        read_only_fields = ['id']
