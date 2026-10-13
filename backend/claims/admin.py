from django.contrib import admin
from .models import Claim, ClaimEvidence

class ClaimEvidenceInline(admin.TabularInline):
    model = ClaimEvidence
    extra = 0

@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ('id', 'report', 'claimant', 'status', 'reviewed_by', 'decision_at', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('claimant__email', 'report__title')
    inlines = [ClaimEvidenceInline]
