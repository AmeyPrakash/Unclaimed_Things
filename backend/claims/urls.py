from django.urls import path
from .views import (
    CreateClaimForReportView,
    MyClaimsView,
    StaffClaimsListView,
    ClaimDetailView,
    AddClaimEvidenceView,
    DecideClaimView,
    CompleteHandoverView
)

urlpatterns = [
    path('reports/<uuid:pk>/claims/', CreateClaimForReportView.as_view(), name='report-claim-create'),
    path('claims/mine/', MyClaimsView.as_view(), name='claims-mine'),
    path('claims/staff/', StaffClaimsListView.as_view(), name='claims-staff'),
    path('claims/<uuid:pk>/', ClaimDetailView.as_view(), name='claim-detail'),
    path('claims/<uuid:pk>/evidence/', AddClaimEvidenceView.as_view(), name='claim-evidence-add'),
    path('claims/<uuid:pk>/complete-handover/', CompleteHandoverView.as_view(), name='claim-complete-handover'),
    path('claims/<uuid:pk>/<str:decision>/', DecideClaimView.as_view(), name='claim-decide'),
]
