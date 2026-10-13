from django.urls import path
from .views import ReportMatchesView, MatchFeedbackView

urlpatterns = [
    path('reports/<uuid:pk>/matches/', ReportMatchesView.as_view(), name='report-matches'),
    path('reports/<uuid:pk>/feedback/', MatchFeedbackView.as_view(), name='report-feedback'),
]
