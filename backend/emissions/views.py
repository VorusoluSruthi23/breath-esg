from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.contrib.auth import authenticate, login
from rest_framework.authtoken.models import Token

from .models import EmissionRecord, IngestionBatch, AuditLog, Tenant, TenantMembership
from .serializers import EmissionRecordSerializer, IngestionBatchSerializer, AuditLogSerializer, TenantSerializer


class LoginView(APIView):
    permission_classe= [AllowAny]
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            membership = TenantMembership.objects.filter(user=user).first()
            return Response({
                'token': token.key,
                'username': user.username,
                'tenant': TenantSerializer(membership.tenant).data if membership else None,
                'role': membership.role if membership else None,
            })
        return Response({'error': 'Invalid credentials'}, status=401)


class EmissionRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = EmissionRecordSerializer

    def get_queryset(self):
        user = self.request.user
        memberships = TenantMembership.objects.filter(user=user).values_list('tenant_id', flat=True)
        qs = EmissionRecord.objects.filter(tenant__in=memberships)

        # Filters
        scope = self.request.query_params.get('scope')
        status_filter = self.request.query_params.get('status')
        source = self.request.query_params.get('source_type')

        if scope:
            qs = qs.filter(scope=scope)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if source:
            qs = qs.filter(source_type=source)

        return qs.select_related('approved_by', 'raw_record')

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        record = self.get_object()
        if record.status == 'locked':
            return Response({'error': 'Record is locked'}, status=400)
        
        before = {'status': record.status}
        record.status = 'approved'
        record.approved_by = request.user
        record.approved_at = timezone.now()
        record.save()

        AuditLog.objects.create(
            record=record, user=request.user, action='approved',
            before_state=before, after_state={'status': 'approved'},
        )
        return Response(EmissionRecordSerializer(record).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        record = self.get_object()
        if record.status == 'locked':
            return Response({'error': 'Record is locked'}, status=400)
        before = {'status': record.status}
        record.status = 'rejected'
        record.save()
        AuditLog.objects.create(
            record=record, user=request.user, action='rejected',
            before_state=before, notes=request.data.get('reason', ''),
        )
        return Response(EmissionRecordSerializer(record).data)

    @action(detail=True, methods=['post'])
    def flag(self, request, pk=None):
        record = self.get_object()
        if record.status == 'locked':
            return Response({'error': 'Record is locked'}, status=400)
        before = {'status': record.status}
        record.status = 'flagged'
        record.flag_reason = request.data.get('reason', '')
        record.save()
        AuditLog.objects.create(
            record=record, user=request.user, action='flagged',
            before_state=before, notes=record.flag_reason,
        )
        return Response(EmissionRecordSerializer(record).data)

    @action(detail=False, methods=['post'])
    def bulk_approve(self, request):
        ids = request.data.get('ids', [])
        records = self.get_queryset().filter(id__in=ids, status__in=['pending', 'flagged'])
        now = timezone.now()
        for r in records:
            before = {'status': r.status}
            r.status = 'approved'
            r.approved_by = request.user
            r.approved_at = now
            r.save()
            AuditLog.objects.create(record=r, user=request.user, action='approved', before_state=before)
        return Response({'approved': records.count()})

    def partial_update(self, request, *args, **kwargs):
        record = self.get_object()
        if record.status == 'locked':
            return Response({'error': 'Locked records cannot be edited'}, status=400)
        before = EmissionRecordSerializer(record).data
        record.is_manually_edited = True
        record.edit_notes = request.data.get('edit_notes', '')
        result = super().partial_update(request, *args, **kwargs)
        AuditLog.objects.create(
            record=record, user=request.user, action='edited',
            before_state=before, after_state=EmissionRecordSerializer(record).data,
        )
        return result


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = TenantMembership.objects.filter(user=request.user).values_list('tenant_id', flat=True)
        qs = EmissionRecord.objects.filter(tenant__in=memberships)

        summary = {
            'total_co2e_kg': float(qs.aggregate(total=Sum('co2e_kg'))['total'] or 0),
            'by_scope': {},
            'by_status': {},
            'by_source': {},
        }

        for scope in [1, 2, 3]:
            scope_qs = qs.filter(scope=scope)
            summary['by_scope'][f'scope_{scope}'] = {
                'co2e_kg': float(scope_qs.aggregate(t=Sum('co2e_kg'))['t'] or 0),
                'count': scope_qs.count(),
            }

        for s in ['pending', 'flagged', 'approved', 'locked', 'rejected']:
            summary['by_status'][s] = qs.filter(status=s).count()

        for src in ['sap_fuel', 'utility_electricity', 'corporate_travel']:
            src_qs = qs.filter(source_type=src)
            summary['by_source'][src] = {
                'co2e_kg': float(src_qs.aggregate(t=Sum('co2e_kg'))['t'] or 0),
                'count': src_qs.count(),
            }

        return Response(summary)


class BatchListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = TenantMembership.objects.filter(user=request.user).values_list('tenant_id', flat=True)
        batches = IngestionBatch.objects.filter(tenant__in=memberships).order_by('-uploaded_at')
        return Response(IngestionBatchSerializer(batches, many=True).data)


class AuditLogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, record_id):
        logs = AuditLog.objects.filter(record_id=record_id).order_by('timestamp')
        return Response(AuditLogSerializer(logs, many=True).data)
