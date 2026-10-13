from django.contrib import admin
from .models import Location, LocationMembership

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'location_type', 'is_active', 'created_at')
    list_filter = ('location_type', 'is_active')
    search_fields = ('name', 'description')

@admin.register(LocationMembership)
class LocationMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'location', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'location')
    search_fields = ('user__email', 'location__name')
