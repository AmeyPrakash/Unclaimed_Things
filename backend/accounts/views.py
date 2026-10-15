from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import login, logout
from .serializers import UserSerializer, LoginSerializer, RegisterSerializer

class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'auth_login'

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return Response({
            "message": "Login successful.",
            "user": UserSerializer(user).data
        })

class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'auth_register'

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user)
        return Response({
            "message": "User registered successfully.",
            "user": UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"message": "Logout successful."})

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"user": UserSerializer(request.user).data})

    def delete(self, request):
        """
        User account self-deletion / right-to-be-forgotten workflow (TRD Section 9).
        Safely withdraws active reports and claims, scrubs identity PII, logs audit event,
        and terminates user session without breaking relational integrity.
        """
        user = request.user
        from audit.models import AuditEvent
        from reports.models import ItemReport, ReportStatus
        from claims.models import Claim, ClaimStatus
        from django.db import transaction

        with transaction.atomic():
            user_reports = ItemReport.objects.filter(created_by=user)
            withdrawn_count = user_reports.filter(status=ReportStatus.OPEN).update(status=ReportStatus.WITHDRAWN)

            user_claims = Claim.objects.filter(claimant=user)
            user_claims.filter(status=ClaimStatus.PENDING).update(status=ClaimStatus.REJECTED)

            user_id_str = str(user.id)
            AuditEvent.objects.create(
                actor=user,
                action="ACCOUNT_DELETED",
                entity_type="User",
                entity_id=user_id_str,
                metadata_redacted={
                    "reason": "User requested right-to-be-forgotten deletion",
                    "open_reports_withdrawn": withdrawn_count
                }
            )

            user.is_active = False
            user.email = f"deleted_{user.id}@anonymized.local"
            user.display_name = "Deactivated User"
            user.set_unusable_password()
            user.save()

            logout(request)

        return Response({
            "message": "Your account and active listings have been successfully withdrawn/deleted per campus data retention policy."
        }, status=status.HTTP_200_OK)

