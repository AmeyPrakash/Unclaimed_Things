from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReportViewSet, CreateLostReportView, CreateFoundReportView, WithdrawReportView, UploadReportImageView

router = DefaultRouter()
router.register(r'reports', ReportViewSet, basename='report')

urlpatterns = [
    path('reports/lost/', CreateLostReportView.as_view(), name='report-lost-create'),
    path('reports/found/', CreateFoundReportView.as_view(), name='report-found-create'),
    path('reports/<uuid:pk>/withdraw/', WithdrawReportView.as_view(), name='report-withdraw'),
    path('reports/<uuid:pk>/images/', UploadReportImageView.as_view(), name='report-upload-image'),
    path('', include(router.urls)),
]
