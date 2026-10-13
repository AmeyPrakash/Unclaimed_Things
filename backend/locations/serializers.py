from rest_framework import serializers
from .models import Location, LocationMembership

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'location_type', 'description', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']

class LocationMembershipSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source='location.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = LocationMembership
        fields = ['id', 'user', 'user_email', 'location', 'location_name', 'role', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']
