from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from reports.models import ItemReport
from .models import MatchFeedback
from .services import MatchingService

class ReportMatchesView(APIView):
    """
    Returns ranked possible matches for a report.
    Adheres strictly to the safe schema from BACKEND_SCHEMA Section 6.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        report = get_object_or_404(ItemReport, pk=pk)
        result = MatchingService.find_matches_for_report(report)
        return Response(result)

class MatchFeedbackView(APIView):
    """
    Records human feedback on match candidates (RELEVANT, NOT_RELEVANT, CLAIMED, RECOVERED).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        report = get_object_or_404(ItemReport, pk=pk)
        candidate_id = request.data.get('candidate_report_id')
        feedback_val = request.data.get('feedback')

        if not candidate_id or not feedback_val:
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "message": "candidate_report_id and feedback are required."}},
                status=status.HTTP_400_BAD_REQUEST
            )

        candidate = get_object_or_404(ItemReport, pk=candidate_id)
        MatchFeedback.objects.create(
            query_report=report,
            candidate_report=candidate,
            actor=request.user,
            feedback=feedback_val.upper()
        )

        return Response({"message": "Feedback recorded successfully."})
