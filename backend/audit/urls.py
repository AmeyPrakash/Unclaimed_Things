from django.urls import path
from .views import (
    AdminOverviewView,
    AdminAuditEventsView,
    AdminReportsListView,
    AdminModerateReportView,
    AdminUsersListView,
    AdminSuspendUserView,
    AdminMetricsExportView,
)

urlpatterns = [
    path('admin/overview/', AdminOverviewView.as_view(), name='admin-overview'),
    path('admin/metrics/export/', AdminMetricsExportView.as_view(), name='admin-metrics-export'),
    path('admin/audit-events/', AdminAuditEventsView.as_view(), name='admin-audit-events'),
    path('admin/reports/', AdminReportsListView.as_view(), name='admin-reports'),
    path('admin/reports/<uuid:pk>/moderate/', AdminModerateReportView.as_view(), name='admin-report-moderate'),
    path('admin/users/', AdminUsersListView.as_view(), name='admin-users'),
    path('admin/users/<uuid:pk>/suspend/', AdminSuspendUserView.as_view(), name='admin-user-suspend'),
]
