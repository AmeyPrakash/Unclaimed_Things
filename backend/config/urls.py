"""
Root URL configuration for The Unclaimed Things Network (UTN).
Base API path: /api/v1/
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

api_v1_patterns = [
    path('', include('common.urls')),
    path('', include('accounts.urls')),
    path('', include('locations.urls')),
    path('', include('reports.urls')),
    path('', include('matching.urls')),
    path('', include('claims.urls')),
    path('', include('custody.urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include(api_v1_patterns)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
