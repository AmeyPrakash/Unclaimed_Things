from django.urls import path
from .views import (
    ReportCustodyHistoryView,
    RequestCustodyTransferView,
    AcceptCustodyTransferView,
    PendingTransfersListView
)

urlpatterns = [
    path('custody/transfers/pending/', PendingTransfersListView.as_view(), name='custody-transfers-pending'),
    path('reports/<uuid:pk>/custody/', ReportCustodyHistoryView.as_view(), name='report-custody-history'),
    path('reports/<uuid:pk>/custody/transfers/', RequestCustodyTransferView.as_view(), name='report-custody-transfer-request'),
    path('custody/transfers/<uuid:pk>/accept/', AcceptCustodyTransferView.as_view(), name='custody-transfer-accept'),
]
