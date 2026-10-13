import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone

class LocationType(models.TextChoices):
    LIBRARY = 'LIBRARY', 'Library'
    SECURITY_OFFICE = 'SECURITY_OFFICE', 'Security Office'
    BUS_SERVICE = 'BUS_SERVICE', 'Bus Service'
    OTHER = 'OTHER', 'Other'

class Location(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, unique=True)
    location_type = models.CharField(
        max_length=30,
        choices=LocationType.choices,
        default=LocationType.OTHER
    )
    description = models.TextField(blank=True, help_text="Safe public description of the location")
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'utn_locations'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_location_type_display()})"

class MembershipRole(models.TextChoices):
    LOCATION_STAFF = 'LOCATION_STAFF', 'Location Staff'
    LOCATION_ADMIN = 'LOCATION_ADMIN', 'Location Admin'

class LocationMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='location_memberships'
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    role = models.CharField(
        max_length=30,
        choices=MembershipRole.choices,
        default=MembershipRole.LOCATION_STAFF
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'utn_location_memberships'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'location', 'role'],
                name='unique_user_location_role'
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.location.name} [{self.role}]"
