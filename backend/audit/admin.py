from django.contrib import admin
from .models import AuditEvent

@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('action', 'entity_type', 'entity_id', 'actor', 'request_id', 'created_at')
    list_filter = ('action', 'entity_type', 'created_at')
    search_fields = ('action', 'entity_id', 'actor__email', 'request_id')
    readonly_fields = ('id', 'actor', 'action', 'entity_type', 'entity_id', 'request_id', 'metadata_redacted', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
