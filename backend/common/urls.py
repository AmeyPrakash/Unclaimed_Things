from django.urls import path
from .views import LivenessCheckView, ReadinessCheckView

urlpatterns = [
    path('health/live/', LivenessCheckView.as_view(), name='health-live'),
    path('health/ready/', ReadinessCheckView.as_view(), name='health-ready'),
]
