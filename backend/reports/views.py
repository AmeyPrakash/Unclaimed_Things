from rest_framework import status, permissions, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from .models import ItemReport, ReportType, ReportStatus, ReportVisibility
from .serializers import PublicItemReportSerializer, LostReportCreateSerializer, FoundReportCreateSerializer
from locations.models import LocationMembership

class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public listings of active reports. Always excludes private fields.
    Supports filtering by report_type, category, status, location.
    """
    serializer_class = PublicItemReportSerializer
    permission_classes = [permissions.AllowAny]

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
