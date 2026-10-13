from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from reports.models import ItemReport, ReportType
from locations.models import Location, LocationMembership
from .models import CustodyEvent, CustodyEventType
from .serializers import CustodyEventSerializer

class ReportCustodyHistoryView(APIView):
    """
    Staff-only view of custody events for a report.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        is_staff = request.user.is_staff or LocationMembership.objects.filter(user=request.user, is_active=True).exists()
        if not is_staff:
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "Only location staff can view custody history."}},
                status=status.HTTP_403_FORBIDDEN
            )

        report = get_object_or_404(ItemReport, pk=pk)
        events = report.custody_events.all().select_related('from_location', 'to_location', 'actor')
        return Response(CustodyEventSerializer(events, many=True).data)

class RequestCustodyTransferView(APIView):
    """
    Initiates a transfer of custody to another participating campus location.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        is_staff = request.user.is_staff or LocationMembership.objects.filter(user=request.user, is_active=True).exists()
        if not is_staff:
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "Only staff can request transfers."}},
                status=status.HTTP_403_FORBIDDEN
            )

        report = get_object_or_404(ItemReport, pk=pk)
        to_location_id = request.data.get('to_location_id')
        if not to_location_id:
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": "to_location_id is required."}},
                status=status.HTTP_400_BAD_REQUEST
            )

        to_location = get_object_or_404(Location, pk=to_location_id)

        event = CustodyEvent.objects.create(
            report=report,
            event_type=CustodyEventType.TRANSFER_REQUESTED,
            from_location=report.current_holding_location,
            to_location=to_location,
            actor=request.user,
            note_private=request.data.get('note_private', '')
        )

        return Response(CustodyEventSerializer(event).data, status=status.HTTP_201_CREATED)

class AcceptCustodyTransferView(APIView):
    """
    Destination staff accepts transfer, updating current_holding_location atomically.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        event = get_object_or_404(CustodyEvent, pk=pk)
        if event.event_type != CustodyEventType.TRANSFER_REQUESTED:
            return Response(
                {"error": {"code": "INVALID_STATE", "message": "Only requested transfers can be accepted."}},
                status=status.HTTP_400_BAD_REQUEST
            )

        report = event.report
        with transaction.atomic():
            report.current_holding_location = event.to_location
            report.save(update_fields=['current_holding_location', 'updated_at'])

            new_event = CustodyEvent.objects.create(
                report=report,
                event_type=CustodyEventType.TRANSFER_ACCEPTED,
                from_location=event.from_location,
                to_location=event.to_location,
                actor=request.user,
                related_event=event,
                note_private=request.data.get('note_private', 'Transfer accepted.')
            )

        return Response(CustodyEventSerializer(new_event).data)
