from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from reports.models import ItemReport, ReportType, ReportStatus
from .models import Claim, ClaimEvidence, ClaimStatus
from .serializers import ClaimSerializer, ClaimCreateSerializer, ClaimEvidenceSerializer
from locations.models import LocationMembership

class CreateClaimForReportView(APIView):
    """
    Submits a private claim on a found item report.
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = 'claim_create'

    def post(self, request, pk):
        report = get_object_or_404(ItemReport, pk=pk)
        if report.report_type != ReportType.FOUND:
            return Response(
                {"error": {"code": "INVALID_REPORT", "message": "Claims can only be filed against found items."}},
                status=status.HTTP_400_BAD_REQUEST
            )
        if report.status != ReportStatus.OPEN:
            return Response(
                {"error": {"code": "REPORT_NOT_OPEN", "message": "This report is no longer open for claims."}},
                status=status.HTTP_400_BAD_REQUEST
            )

        statement = request.data.get('claimant_statement', '').strip()
        if not statement:
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": "claimant_statement is required."}},
                status=status.HTTP_400_BAD_REQUEST
            )

        claim = Claim.objects.create(
            report=report,
            claimant=request.user,
            claimant_statement=statement
        )
        return Response(ClaimSerializer(claim).data, status=status.HTTP_201_CREATED)

class MyClaimsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        claims = Claim.objects.filter(claimant=request.user).select_related('report')
        return Response(ClaimSerializer(claims, many=True).data)

class StaffClaimsListView(APIView):
    """
    Staff-only view: lists claims for items held at locations assigned to the staff member.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        is_staff = request.user.is_staff or LocationMembership.objects.filter(user=request.user, is_active=True).exists()
        if not is_staff:
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "Only location staff can view claims queue."}},
                status=status.HTTP_403_FORBIDDEN
            )

        if request.user.is_staff:
            claims = Claim.objects.all().select_related('report', 'claimant')
        else:
            staff_locations = LocationMembership.objects.filter(
                user=request.user, is_active=True
            ).values_list('location_id', flat=True)
            claims = Claim.objects.filter(
                report__current_holding_location_id__in=staff_locations
            ).select_related('report', 'claimant')

        return Response(ClaimSerializer(claims, many=True).data)

class ClaimDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        claim = get_object_or_404(Claim, pk=pk)
        is_staff = request.user.is_staff or LocationMembership.objects.filter(user=request.user, is_active=True).exists()
        
        if claim.claimant != request.user and not is_staff:
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "You are not authorized to view this claim."}},
                status=status.HTTP_403_FORBIDDEN
            )
        return Response(ClaimSerializer(claim).data)

class AddClaimEvidenceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        claim = get_object_or_404(Claim, pk=pk)
        if claim.claimant != request.user and not request.user.is_staff:
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "Cannot add evidence to another user's claim."}},
                status=status.HTTP_403_FORBIDDEN
            )
        
        evidence_type = request.data.get('evidence_type', 'TEXT')
        private_value = request.data.get('private_value', '').strip()
        if not private_value:
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": "private_value cannot be empty."}},
                status=status.HTTP_400_BAD_REQUEST
            )

        evidence = ClaimEvidence.objects.create(
            claim=claim,
            evidence_type=evidence_type,
            private_value=private_value,
            created_by=request.user
        )
        return Response(ClaimEvidenceSerializer(evidence).data, status=status.HTTP_201_CREATED)

class DecideClaimView(APIView):
    """
    Staff decision endpoint (approve / reject).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, decision):
        is_staff = request.user.is_staff or LocationMembership.objects.filter(user=request.user, is_active=True).exists()
        if not is_staff:
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "Only staff can review and decide claims."}},
                status=status.HTTP_403_FORBIDDEN
            )

        claim = get_object_or_404(Claim, pk=pk)
        decision = decision.lower()
        if decision == 'approve':
            claim.status = ClaimStatus.APPROVED
        elif decision == 'reject':
            claim.status = ClaimStatus.REJECTED
        else:
            return Response(
                {"error": {"code": "INVALID_DECISION", "message": "Decision must be 'approve' or 'reject'."}},
                status=status.HTTP_400_BAD_REQUEST
            )

        claim.reviewed_by = request.user
        claim.review_note_private = request.data.get('note', '')
        claim.decision_at = timezone.now()
        claim.save()

        from audit.models import AuditEvent
        AuditEvent.objects.create(
            actor=request.user,
            action=f"CLAIM_{decision.upper()}",
            entity_type="Claim",
            entity_id=str(claim.id),
            metadata_redacted={
                "report_id": str(claim.report.id),
                "decision": decision,
                "claimant_email": claim.claimant.email
            }
        )

        return Response(ClaimSerializer(claim).data)

class CompleteHandoverView(APIView):
    """
    Completes item handover to claimant.
    Atomically updates Claim to COMPLETED, Report to RETURNED, and logs a CustodyEvent.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        is_staff = request.user.is_staff or LocationMembership.objects.filter(user=request.user, is_active=True).exists()
        if not is_staff:
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "Only staff can complete handovers."}},
                status=status.HTTP_403_FORBIDDEN
            )

        claim = get_object_or_404(Claim, pk=pk)
        if claim.status != ClaimStatus.APPROVED:
            return Response(
                {"error": {"code": "CLAIM_NOT_APPROVED", "message": "Handover can only be completed for approved claims."}},
                status=status.HTTP_400_BAD_REQUEST
            )

        from django.db import transaction
        from custody.models import CustodyEvent, CustodyEventType
        from audit.models import AuditEvent

        with transaction.atomic():
            claim.status = ClaimStatus.COMPLETED
            claim.save(update_fields=['status', 'updated_at'])

            report = claim.report
            report.status = ReportStatus.RETURNED
            report.save(update_fields=['status', 'updated_at'])

            CustodyEvent.objects.create(
                report=report,
                event_type=CustodyEventType.HANDOVER_COMPLETED,
                from_location=report.current_holding_location,
                to_location=None,
                actor=request.user,
                note_private=f"Handover completed to claimant {claim.claimant.email}"
            )

            AuditEvent.objects.create(
                actor=request.user,
                action="HANDOVER_COMPLETED",
                entity_type="Claim",
                entity_id=str(claim.id),
                metadata_redacted={
                    "report_id": str(report.id),
                    "holding_location": report.current_holding_location.name if report.current_holding_location else None,
                    "claimant_email": claim.claimant.email
                }
            )

        return Response({"message": "Handover successfully completed and item marked as RETURNED."})
