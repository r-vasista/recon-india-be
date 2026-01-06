from django.urls import path
from reporter.views import (
    ReporterProfileAPIView, AdminReporterListAPIView, AdminReporterDetailAPIView, AdminReporterAssignPortalsAPIView, 
    AdminReporterActionAPIView
)

urlpatterns = [
    # Reporter endpoints (authenticated reporter only)
    path('profile/', ReporterProfileAPIView.as_view(), name='reporter-profile'),
    
    # Admin endpoints (authenticated admin only)
    path('admin/reporters/', AdminReporterListAPIView.as_view(), name='admin-reporter-list'),
    path('admin/reporters/<int:reporter_id>/', AdminReporterDetailAPIView.as_view(), name='admin-reporter-detail'),
    path('admin/reporters/action/<int:reporter_id>/', AdminReporterActionAPIView.as_view(), name='admin-reporter-action'),
    path('admin/reporters/assign-portals/<int:reporter_id>/', AdminReporterAssignPortalsAPIView.as_view(), name='admin-reporter-assign-portals'),
]
