from django.contrib import admin
from .models import CustodyEvent

@admin.register(CustodyEvent)
class CustodyEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'report', 'event_type', 'from_location', 'to_location', 'actor', 'occurred_at')
    list_filter = ('event_type', 'occurred_at')
    search_fields = ('report__title', 'actor__email')
