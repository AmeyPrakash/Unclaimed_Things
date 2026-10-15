from rest_framework import status, permissions, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.db.models import Q
from .models import AuditEvent
from .serializers import AuditEventSerializer, AdminReportSerializer, AdminUserSerializer
from .services import PilotMetricsService
from reports.models import ItemReport, ReportType, ReportStatus, ReportVisibility, ItemEmbedding, ReportAbuseFlag
from claims.models import Claim, ClaimStatus
from custody.models import CustodyEvent, CustodyEventType
from accounts.models import User
from locations.models import Location

class IsAdminUser(permissions.BasePermission):
    """
    Requires that the authenticated user is a staff member or superuser.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser))

class AdminOverviewView(APIView):
    """
    GET /api/v1/admin/overview/
    Returns system-wide operational metrics, counts, and health status.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        days_param = request.query_params.get('days')
        days = int(days_param) if days_param and days_param.isdigit() else None

        # Report metrics
        total_reports = ItemReport.objects.count()
        lost_open = ItemReport.objects.filter(report_type=ReportType.LOST, status=ReportStatus.OPEN).count()
        found_open = ItemReport.objects.filter(report_type=ReportType.FOUND, status=ReportStatus.OPEN).count()
        returned_reports = ItemReport.objects.filter(status=ReportStatus.RETURNED).count()
        withdrawn_reports = ItemReport.objects.filter(status=ReportStatus.WITHDRAWN).count()
        expired_reports = ItemReport.objects.filter(status=ReportStatus.EXPIRED).count()
        hidden_reports = ItemReport.objects.filter(visibility=ReportVisibility.HIDDEN).count()
        removed_reports = ItemReport.objects.filter(visibility=ReportVisibility.REMOVED).count()
        total_flagged_reports = ItemReport.objects.filter(abuse_flags__isnull=False).distinct().count()
        total_abuse_flags = ReportAbuseFlag.objects.count()

        # Claim metrics
        total_claims = Claim.objects.count()
        pending_claims = Claim.objects.filter(status=ClaimStatus.PENDING).count()
        approved_claims = Claim.objects.filter(status=ClaimStatus.APPROVED).count()
        completed_claims = Claim.objects.filter(status=ClaimStatus.COMPLETED).count()
        rejected_claims = Claim.objects.filter(status=ClaimStatus.REJECTED).count()

        # Custody transfers
        total_transfers = CustodyEvent.objects.filter(
            event_type__in=[CustodyEventType.TRANSFER_REQUESTED, CustodyEventType.TRANSFER_ACCEPTED]
        ).count()
        pending_transfers = CustodyEvent.objects.filter(event_type=CustodyEventType.TRANSFER_REQUESTED).count()

        # User metrics
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        suspended_users = User.objects.filter(is_active=False).count()
        staff_users = User.objects.filter(is_staff=True).count()

        # Location metrics
        total_locations = Location.objects.filter(is_active=True).count()

        # System & AI
        embeddings_count = ItemEmbedding.objects.count()
        audit_events_count = AuditEvent.objects.count()

        return Response({
            "reports": {
                "total": total_reports,
                "lost_open": lost_open,
                "found_open": found_open,
                "returned": returned_reports,
                "withdrawn": withdrawn_reports,
                "expired": expired_reports,
                "hidden": hidden_reports,
                "removed": removed_reports,
                "flagged": total_flagged_reports,
                "total_abuse_flags": total_abuse_flags
            },
            "claims": {
                "total": total_claims,
                "pending": pending_claims,
                "approved": approved_claims,
                "completed": completed_claims,
                "rejected": rejected_claims
            },
            "custody": {
                "total_transfers": total_transfers,
                "pending_transfers": pending_transfers
            },
            "users": {
                "total": total_users,
                "active": active_users,
                "suspended": suspended_users,
                "staff": staff_users
            },
            "locations": {
                "active_count": total_locations
            },
            "system": {
                "nim_enabled": bool(settings.NIM_ENABLED),
                "nim_model": getattr(settings, 'NIM_EMBEDDING_MODEL', 'unknown'),
                "embeddings_count": embeddings_count,
                "audit_events_count": audit_events_count
            },
            "pilot_metrics": PilotMetricsService.compute_metrics(days=days)
        })

class AdminMetricsExportView(APIView):
    """
    GET /api/v1/admin/metrics/export/?format=csv|json[&days=30]
    Allows campus administrators to export pilot KPI and success metrics per PRD Section 9.
    """
    permission_classes = [IsAdminUser]

    def perform_content_negotiation(self, request, force=False):
        # Prevent DRF DefaultContentNegotiation from raising NotFound when query param is ?format=csv
        renderers = self.get_renderers()
        return (renderers[0], renderers[0].media_type)

    def get(self, request):
        fmt = request.query_params.get('format', 'json').lower()
        days_param = request.query_params.get('days')
        days = int(days_param) if days_param and days_param.isdigit() else None

        metrics = PilotMetricsService.compute_metrics(days=days)

        if fmt == 'csv':
            from django.http import HttpResponse
            csv_data = PilotMetricsService.generate_csv(metrics)
            response = HttpResponse(csv_data, content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = 'attachment; filename="utn_pilot_metrics.csv"'
            return response

        return Response(metrics)

class AdminAuditEventsView(generics.ListAPIView):
    """
    GET /api/v1/admin/audit-events/
    Paginated audit log with filtering by action, entity_type, and search query.
    """
    permission_classes = [IsAdminUser]
    serializer_class = AuditEventSerializer

    def get_queryset(self):
        qs = AuditEvent.objects.select_related('actor').all()
        action = self.request.query_params.get('action')
        entity_type = self.request.query_params.get('entity_type')
        search = self.request.query_params.get('search')

        if action:
            qs = qs.filter(action__icontains=action)
        if entity_type:
            qs = qs.filter(entity_type__iexact=entity_type)
        if search:
            qs = qs.filter(
                Q(action__icontains=search) |
                Q(entity_id__icontains=search) |
                Q(request_id__icontains=search) |
                Q(actor__email__icontains=search)
            )
        return qs[:100]

class AdminReportsListView(generics.ListAPIView):
    """
    GET /api/v1/admin/reports/
    Lists all reports regardless of visibility status for moderation purposes.
    """
    permission_classes = [IsAdminUser]
    serializer_class = AdminReportSerializer

    def get_queryset(self):
        qs = ItemReport.objects.select_related(
            'created_by', 'last_seen_location', 'found_location', 'current_holding_location'
        ).all().order_by('-created_at')

        visibility = self.request.query_params.get('visibility')
        report_type = self.request.query_params.get('report_type')
        status_param = self.request.query_params.get('status')
        flagged_param = self.request.query_params.get('flagged')
        search = self.request.query_params.get('search')

        if visibility:
            qs = qs.filter(visibility=visibility.upper())
        if report_type:
            qs = qs.filter(report_type=report_type.upper())
        if status_param:
            qs = qs.filter(status=status_param.upper())
        if flagged_param and flagged_param.lower() in ('true', '1', 'yes'):
            qs = qs.filter(abuse_flags__isnull=False).distinct()
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(public_description__icontains=search) |
                Q(created_by__email__icontains=search)
            )
        return qs[:100]

class AdminModerateReportView(APIView):
    """
    POST /api/v1/admin/reports/<uuid:pk>/moderate/
    Moderates report visibility (ACTIVE, HIDDEN, REMOVED) and records an AuditEvent.
    """
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        report = get_object_or_404(ItemReport, pk=pk)
        new_visibility = request.data.get('visibility', '').upper()
        reason = request.data.get('reason', '').strip()

        valid_visibilities = [choice[0] for choice in ReportVisibility.choices]
        if new_visibility not in valid_visibilities:
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": f"visibility must be one of {valid_visibilities}."}},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_visibility = report.visibility
        report.visibility = new_visibility
        report.save(update_fields=['visibility', 'updated_at'])

        # Log immutable audit event
        AuditEvent.objects.create(
            actor=request.user,
            action=f"REPORT_MODERATED_{new_visibility}",
            entity_type="ItemReport",
            entity_id=str(report.id),
            metadata_redacted={
                "title": report.title,
                "old_visibility": old_visibility,
                "new_visibility": new_visibility,
                "reason": reason or "Administrative moderation action"
            }
        )

        return Response({
            "message": f"Report visibility successfully updated to {new_visibility}.",
            "report": AdminReportSerializer(report).data
        })

class AdminUsersListView(generics.ListAPIView):
    """
    GET /api/v1/admin/users/
    List registered users for management.
    """
    permission_classes = [IsAdminUser]
    serializer_class = AdminUserSerializer

    def get_queryset(self):
        qs = User.objects.prefetch_related('location_memberships__location').all().order_by('-created_at')
        search = self.request.query_params.get('search')
        is_active = self.request.query_params.get('is_active')
        is_staff = self.request.query_params.get('is_staff')

        if search:
            qs = qs.filter(
                Q(email__icontains=search) |
                Q(display_name__icontains=search)
            )
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')
        if is_staff is not None:
            qs = qs.filter(is_staff=is_staff.lower() == 'true')

        return qs[:100]

class AdminSuspendUserView(APIView):
    """
    POST /api/v1/admin/users/<uuid:pk>/suspend/
    Suspends or reactivates a user account, logging an AuditEvent.
    """
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "Administrators cannot suspend their own account."}},
                status=status.HTTP_400_BAD_REQUEST
            )
        if user.is_superuser and not request.user.is_superuser:
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "Only superusers can modify other superusers."}},
                status=status.HTTP_403_FORBIDDEN
            )

        is_active = request.data.get('is_active')
        if is_active is None:
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": "is_active boolean is required."}},
                status=status.HTTP_400_BAD_REQUEST
            )

        is_active = bool(is_active)
        reason = request.data.get('reason', '').strip()

        user.is_active = is_active
        user.save(update_fields=['is_active', 'updated_at'])

        action_name = "USER_ACTIVATED" if is_active else "USER_SUSPENDED"
        AuditEvent.objects.create(
            actor=request.user,
            action=action_name,
            entity_type="User",
            entity_id=str(user.id),
            metadata_redacted={
                "target_email": user.email,
                "is_active": is_active,
                "reason": reason or ("Account reactivation" if is_active else "Suspended by administrator")
            }
        )

        return Response({
            "message": f"User status updated to {'Active' if is_active else 'Suspended'}.",
            "user": AdminUserSerializer(user).data
        })
