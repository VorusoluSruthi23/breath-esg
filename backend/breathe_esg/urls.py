# from django.contrib import admin
# from django.urls import path, include
# from rest_framework.routers import DefaultRouter
# from emissions.views import EmissionRecordViewSet, LoginView, DashboardSummaryView, BatchListView, AuditLogView
# from ingestion.views import IngestSAPView, IngestUtilityView, IngestTravelView

# router = DefaultRouter()
# router.register(r'records', EmissionRecordViewSet, basename='records')

# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('api/auth/login/', LoginView.as_view()),
#     path('api/', include(router.urls)),
#     path('api/ingest/sap/', IngestSAPView.as_view()),
#     path('api/ingest/utility/', IngestUtilityView.as_view()),
#     path('api/ingest/travel/', IngestTravelView.as_view()),
#     path('api/dashboard/summary/', DashboardSummaryView.as_view()),
#     path('api/batches/', BatchListView.as_view()),
#     path('api/records/<uuid:record_id>/audit/', AuditLogView.as_view()),
# ]

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter
from emissions.views import EmissionRecordViewSet, LoginView, DashboardSummaryView, BatchListView, AuditLogView
from ingestion.views import IngestSAPView, IngestUtilityView, IngestTravelView

def health(request):
    return JsonResponse({'status': 'ok'})

router = DefaultRouter()
router.register(r'records', EmissionRecordViewSet, basename='records')

urlpatterns = [
    path('health/', health),
    path('admin/', admin.site.urls),
    path('api/auth/login/', LoginView.as_view()),
    path('api/', include(router.urls)),
    path('api/ingest/sap/', IngestSAPView.as_view()),
    path('api/ingest/utility/', IngestUtilityView.as_view()),
    path('api/ingest/travel/', IngestTravelView.as_view()),
    path('api/dashboard/summary/', DashboardSummaryView.as_view()),
    path('api/batches/', BatchListView.as_view()),
    path('api/records/<uuid:record_id>/audit/', AuditLogView.as_view()),
]
