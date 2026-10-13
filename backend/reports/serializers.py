from rest_framework import serializers
from .models import ItemReport, ReportPrivateDetail, ReportImage, ReportType, ReportStatus
from locations.serializers import LocationSerializer
from locations.models import Location

class ReportImageSerializer(serializers.ModelSerializer):
    url = serializers.ImageField(source='image_file', read_only=True)

    class Meta:
        model = ReportImage
        fields = ['id', 'url', 'content_type', 'size_bytes', 'created_at']
        read_only_fields = fields

class PublicItemReportSerializer(serializers.ModelSerializer):
    """
    Safe public serializer for browse, search, and candidate lists.
    Guaranteed: NO private descriptions, serial numbers, or claimant PII.
    """
    last_seen_location = LocationSerializer(read_only=True)
    found_location = LocationSerializer(read_only=True)
    current_holding_location = LocationSerializer(read_only=True)
    images = ReportImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ItemReport
        fields = [
            'id', 'report_type', 'category', 'title', 'public_description',
            'last_seen_at', 'found_at', 'last_seen_location', 'found_location',
            'current_holding_location', 'status', 'images', 'created_at'
        ]
        read_only_fields = fields

class LostReportCreateSerializer(serializers.ModelSerializer):
    """
    Submitted by user to report a lost item.
    Private fields are cleanly isolated into ReportPrivateDetail.
    """
    private_description = serializers.CharField(write_only=True, required=False, allow_blank=True)
    distinguishing_details = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = ItemReport
        fields = [
            'id', 'category', 'title', 'public_description',
            'last_seen_at', 'last_seen_location',
            'private_description', 'distinguishing_details',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        private_desc = validated_data.pop('private_description', '')
        distinguishing = validated_data.pop('distinguishing_details', {})
        request = self.context.get('request')
        
        report = ItemReport.objects.create(
            report_type=ReportType.LOST,
            created_by=request.user if request and request.user.is_authenticated else None,
            **validated_data
        )

        if private_desc or distinguishing:
            ReportPrivateDetail.objects.create(
                report=report,
                private_description=private_desc,
                distinguishing_details=distinguishing
            )

        return report

class FoundReportCreateSerializer(serializers.ModelSerializer):
    """
    Submitted by authorized location staff to register a found item.
    """
    private_description = serializers.CharField(write_only=True, required=False, allow_blank=True)
    distinguishing_details = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = ItemReport
        fields = [
            'id', 'category', 'title', 'public_description',
            'found_at', 'found_location', 'current_holding_location',
            'private_description', 'distinguishing_details',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        private_desc = validated_data.pop('private_description', '')
        distinguishing = validated_data.pop('distinguishing_details', {})
        request = self.context.get('request')

        report = ItemReport.objects.create(
            report_type=ReportType.FOUND,
            created_by=request.user if request and request.user.is_authenticated else None,
            **validated_data
        )

        if private_desc or distinguishing:
            ReportPrivateDetail.objects.create(
                report=report,
                private_description=private_desc,
                distinguishing_details=distinguishing
            )

        return report
