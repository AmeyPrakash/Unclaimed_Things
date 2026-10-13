from rest_framework import viewsets, permissions
from .models import Location, LocationMembership
from .serializers import LocationSerializer, LocationMembershipSerializer

class IsLocationAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and (
            request.user.is_staff or 
            LocationMembership.objects.filter(user=request.user, role='LOCATION_ADMIN', is_active=True).exists()
        ))

class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.filter(is_active=True)
    serializer_class = LocationSerializer
    permission_classes = [IsLocationAdminOrReadOnly]

    def get_queryset(self):
        # Admin can view all including inactive locations
        if self.request.user.is_authenticated and self.request.user.is_staff:
            return Location.objects.all()
        return Location.objects.filter(is_active=True)
