from django.db import connection
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status

class LivenessCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok", "service": "utn-backend"})

class ReadinessCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        checks = {
            "database": "unknown",
            "pgvector": "unknown",
            "nim_configured": bool(settings.NIM_ENABLED and settings.NIM_API_KEY)
        }
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                checks["database"] = "healthy"
                
                cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
                row = cursor.fetchone()
                checks["pgvector"] = "installed" if row else "not_installed"
        except Exception as e:
            checks["database"] = f"unhealthy: {str(e)}"
            return Response({"status": "degraded", "checks": checks}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({"status": "ready", "checks": checks})
