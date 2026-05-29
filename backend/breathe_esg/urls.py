from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter
from emissions.views import EmissionRecordViewSet, LoginView, DashboardSummaryView, BatchListView, AuditLogView
from ingestion.views import IngestSAPView, IngestUtilityView, IngestTravelView

def health(request):
    return JsonResponse({'status': 'ok'})

def setup(request):
    try:
        from django.contrib.auth.models import User
        from rest_framework.authtoken.models import Token
        from emissions.models import Tenant, TenantMembership
        tenant, _ = Tenant.objects.get_or_create(name='Acme Corp', slug='acme-corp')
        user, _ = User.objects.get_or_create(username='analyst')
        user.set_password('demo1234')
        user.save()
        Token.objects.get_or_create(user=user)
        TenantMembership.objects.get_or_create(user=user, tenant=tenant, defaults={'role': 'analyst'})
        admin_user, _ = User.objects.get_or_create(username='admin')
        admin_user.set_password('admin1234')
        admin_user.is_superuser = True
        admin_user.is_staff = True
        admin_user.save()
        Token.objects.get_or_create(user=admin_user)
        TenantMembership.objects.get_or_create(user=admin_user, tenant=tenant, defaults={'role': 'admin'})
        return JsonResponse({'status': 'ok', 'message': 'Demo users created', 'login': 'analyst / demo1234'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

router = DefaultRouter()
router.register(r'records', EmissionRecordViewSet, basename='records')

urlpatterns = [
    path('health/', health),
    path('setup/', setup),
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
