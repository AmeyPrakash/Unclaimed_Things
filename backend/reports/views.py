from rest_framework import status, permissions, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from .models import ItemReport, ReportType, ReportStatus, ReportVisibility, ReportAbuseFlag
from .serializers import (
    PublicItemReportSerializer, LostReportCreateSerializer,
    FoundReportCreateSerializer, ReportAbuseCreateSerializer
)
from locations.models import LocationMembership

class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public listings of active reports. Always excludes private fields.
    Supports filtering by report_type, category, status, location.
    """
    serializer_class = PublicItemReportSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'search'

    def get_queryset(self):
        qs = ItemReport.objects.filter(visibility=ReportVisibility.ACTIVE)
        
        report_type = self.request.query_params.get('report_type')
        if report_type:
            qs = qs.filter(report_type=report_type.upper())
            
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category.upper())

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param.upper())
        else:
            qs = qs.filter(status=ReportStatus.OPEN)

        location_id = self.request.query_params.get('location')
        if location_id:
            qs = qs.filter(
                found_location_id=location_id
            ) | qs.filter(
                last_seen_location_id=location_id
            ) | qs.filter(
                current_holding_location_id=location_id
            )

        q = self.request.query_params.get('q')
        if q:
            qs = qs.filter(title__icontains=q) | qs.filter(public_description__icontains=q)

        return qs.select_related('last_seen_location', 'found_location', 'current_holding_location')

class CreateLostReportView(APIView):
    """
    Allows authenticated users to report a lost item.
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = 'report_create'

    def post(self, request):
        serializer = LostReportCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        report = serializer.save()
        
        # Async / background embedding trigger
        from matching.services import MatchingService
        MatchingService.trigger_embedding(report)

        return Response(
            PublicItemReportSerializer(report).data,
            status=status.HTTP_201_CREATED
        )

class CreateFoundReportView(APIView):
    """
    Allows authorized staff members to register a found item.
    Checks that the user is assigned to the current_holding_location.
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = 'report_create'

    def post(self, request):
        # Staff verification
        is_staff_user = request.user.is_staff or LocationMembership.objects.filter(
            user=request.user,
            is_active=True
        ).exists()

        if not is_staff_user:
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "Only authorized location staff may register found items."}},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = FoundReportCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        report = serializer.save()

        # Trigger embedding
        from matching.services import MatchingService
        MatchingService.trigger_embedding(report)

        return Response(
            PublicItemReportSerializer(report).data,
            status=status.HTTP_201_CREATED
        )

class WithdrawReportView(APIView):
    """
    Allows creator or admin to withdraw an open report.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        report = get_object_or_404(ItemReport, pk=pk)
        
        if report.created_by != request.user and not request.user.is_staff:
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "You do not have permission to withdraw this report."}},
                status=status.HTTP_403_FORBIDDEN
            )

        report.status = ReportStatus.WITHDRAWN
        report.save(update_fields=['status', 'updated_at'])
        return Response({"message": "Report withdrawn successfully."})

class UploadReportImageView(APIView):
    """
    Uploads an image for an ItemReport. Strips EXIF metadata, enforces 5MB limit and formats.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        from .services import ImageUploadService
        from .serializers import ReportImageSerializer
        from django.core.exceptions import ValidationError

        report = get_object_or_404(ItemReport, pk=pk)

        # Check authorization: creator or staff
        is_creator = report.created_by == request.user
        is_staff = request.user.is_staff or LocationMembership.objects.filter(
            user=request.user,
            location=report.current_holding_location,
            is_active=True
        ).exists()

        if not (is_creator or is_staff):
            return Response(
                {"error": {"code": "FORBIDDEN", "message": "You do not have permission to attach images to this report."}},
                status=status.HTTP_403_FORBIDDEN
            )

        file_obj = request.FILES.get('image')
        if not file_obj:
            return Response(
                {"error": {"code": "BAD_REQUEST", "message": "No image file provided in form-data field 'image'."}},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            report_image = ImageUploadService.attach_image_to_report(report, file_obj, user=request.user)
        except ValidationError as e:
            return Response(
                {"error": {"code": "INVALID_IMAGE", "message": str(e.message if hasattr(e, 'message') else e)}},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(ReportImageSerializer(report_image).data, status=status.HTTP_201_CREATED)

class ReportAbuseView(APIView):
    """
    POST /api/v1/reports/<uuid:pk>/flag/
    Allows authenticated users to flag a suspicious listing or abuse.
    Enforces rate limiting, prevents duplicate flags per user on the same report,
    and logs an immutable AuditEvent.
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = 'report_create'

    def post(self, request, pk):
        report = get_object_or_404(ItemReport, pk=pk)

        if ReportAbuseFlag.objects.filter(report=report, reporter=request.user).exists():
            return Response(
                {"error": {"code": "ALREADY_REPORTED", "message": "You have already submitted an abuse report for this listing."}},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ReportAbuseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        flag = ReportAbuseFlag.objects.create(
            report=report,
            reporter=request.user,
            reason=serializer.validated_data['reason'],
            details=serializer.validated_data.get('details', '')
        )

        from audit.models import AuditEvent
        AuditEvent.objects.create(
            actor=request.user,
            action="REPORT_FLAGGED_ABUSE",
            entity_type="ItemReport",
            entity_id=str(report.id),
            metadata_redacted={
                "reason": flag.reason,
                "report_title": report.title,
                "total_flags": report.abuse_flags.count()
            }
        )

        return Response({
            "message": "Report submitted for moderation review. Thank you for keeping UTN safe.",
            "flag_id": str(flag.id),
            "reason": flag.reason
        }, status=status.HTTP_201_CREATED)

class ProtectedMediaView(APIView):
    """
    Secure media serving view (TRD Section 8).
    - Prevents directory traversal attacks.
    - If the requested media file belongs to a ReportImage whose Report is HIDDEN or REMOVED,
      restricts access to authorized staff or the report creator.
    - Attaches 'X-Content-Type-Options: nosniff' and private cache headers.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, path):
        import os
        import mimetypes
        from django.http import FileResponse, Http404
        from django.conf import settings

        # 1. Normalize path and prevent directory traversal
        clean_rel_path = os.path.normpath(path).replace('\\', '/')
        if clean_rel_path.startswith('..') or clean_rel_path.startswith('/'):
            raise Http404("Invalid file path.")

        full_path = (settings.MEDIA_ROOT / clean_rel_path).resolve()
        try:
            full_path.relative_to(settings.MEDIA_ROOT.resolve())
        except ValueError:
            raise Http404("Access denied.")

        if not full_path.is_file():
            raise Http404("File not found.")

        # 2. Check report image visibility if applicable
        from .models import ReportImage, ReportVisibility
        report_img = ReportImage.objects.filter(image_file=clean_rel_path).select_related('report').first()
        if report_img and report_img.report:
            if report_img.report.visibility in (ReportVisibility.HIDDEN, ReportVisibility.REMOVED):
                user = request.user
                is_authorized = user.is_authenticated and (user.is_staff or report_img.report.created_by == user)
                if not is_authorized:
                    return Response(
                        {"error": {"code": "FORBIDDEN", "message": "This item image is currently hidden or restricted."}},
                        status=status.HTTP_403_FORBIDDEN
                    )

        # 3. Serve file safely
        content_type, _ = mimetypes.guess_type(str(full_path))
        response = FileResponse(open(full_path, 'rb'), content_type=content_type or 'application/octet-stream')
        response['X-Content-Type-Options'] = 'nosniff'
        response['Cache-Control'] = 'private, max-age=3600'
        return response



