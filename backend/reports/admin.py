from django.contrib import admin
from .models import ItemReport, ReportPrivateDetail, ReportImage, ItemEmbedding

class ReportPrivateDetailInline(admin.StackedInline):
    model = ReportPrivateDetail
    can_delete = False

class ReportImageInline(admin.TabularInline):
    model = ReportImage
    extra = 0

class ItemEmbeddingInline(admin.StackedInline):
    model = ItemEmbedding
    can_delete = False
    readonly_fields = ('embedding_status', 'model_name', 'created_at', 'updated_at')

@admin.register(ItemReport)
class ItemReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'report_type', 'category', 'status', 'visibility', 'created_by', 'created_at')
    list_filter = ('report_type', 'category', 'status', 'visibility')
    search_fields = ('title', 'public_description')
    inlines = [ReportPrivateDetailInline, ReportImageInline, ItemEmbeddingInline]
