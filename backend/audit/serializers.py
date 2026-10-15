from rest_framework import serializers
from .models import AuditEvent
from reports.models import ItemReport
from accounts.models import User
from locations.models import LocationMembership

class AuditEventSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source='actor.email', read_only=True, default=None)
    actor_name = serializers.CharField(source='actor.display_name', read_only=True, default='')

    class Meta:
        model = AuditEvent
        fields = [
            'id',
            'actor',
            'actor_email',
            'actor_name',
            'action',
            'entity_type',
            'entity_id',
            'request_id',
            'metadata_redacted',
            'created_at'
        ]
        read_only_fields = fields

class AdminReportSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True, default=None)
    last_seen_location_name = serializers.CharField(source='last_seen_location.name', read_only=True, default=None)
    found_location_name = serializers.CharField(source='found_location.name', read_only=True, default=None)
    current_holding_location_name = serializers.CharField(source='current_holding_location.name', read_only=True, default=None)

    class Meta:
        model = ItemReport
        fields = [
            'id',
            'report_type',
            'category',
            'title',
            'public_description',
            'status',
            'visibility',
            'last_seen_at',
            'found_at',
            'last_seen_location_name',
            'found_location_name',
            'current_holding_location_name',
            'created_by_email',
            'created_at',
            'updated_at'
        ]

class AdminUserMembershipSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source='location.name', read_only=True)

    class Meta:
        model = LocationMembership
        fields = ['id', 'location_name', 'role', 'is_active']

class AdminUserSerializer(serializers.ModelSerializer):
    memberships = AdminUserMembershipSerializer(source='location_memberships', many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'display_name',
            'is_active',
            'is_staff',
            'is_superuser',
            'created_at',
            'updated_at',
            'memberships'
        ]
