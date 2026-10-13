from rest_framework import serializers
from .models import CustodyEvent

class CustodyEventSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source='actor.email', read_only=True)
    from_location_name = serializers.CharField(source='from_location.name', read_only=True)
    to_location_name = serializers.CharField(source='to_location.name', read_only=True)

    class Meta:
        model = CustodyEvent
        fields = [
            'id', 'report', 'event_type', 'from_location', 'from_location_name',
            'to_location', 'to_location_name', 'actor', 'actor_email',
            'note_private', 'occurred_at', 'created_at'
        ]
        read_only_fields = ['id', 'actor', 'created_at']
