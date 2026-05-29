"""
Ingestion API views — handles file uploads and triggers parsing
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from emissions.models import Tenant, IngestionBatch, RawRecord, EmissionRecord, AuditLog, TenantMembership
from .sap_parser import parse_sap_csv
from .utility_parser import parse_utility_csv
from .travel_parser import parse_travel_json, parse_travel_csv


def get_tenant(request):
    """Get tenant from query param or user's first membership."""
    tenant_slug = request.query_params.get('tenant') or request.data.get('tenant')
    if tenant_slug:
        return Tenant.objects.get(slug=tenant_slug)
    membership = TenantMembership.objects.filter(user=request.user).first()
    if membership:
        return membership.tenant
    raise Tenant.DoesNotExist("No tenant found for user")


class IngestSAPView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file uploaded'}, status=400)

        try:
            tenant = get_tenant(request)
        except Tenant.DoesNotExist:
            return Response({'error': 'Tenant not found'}, status=404)

        batch = IngestionBatch.objects.create(
            tenant=tenant,
            source_type='sap_fuel',
            status='processing',
            uploaded_by=request.user,
            original_filename=file.name,
        )

        try:
            content = file.read()
            results, errors = parse_sap_csv(content, batch.id)
            _save_results(batch, results, request.user)
            batch.status = 'completed'
            batch.save()
            return Response({
                'batch_id': str(batch.id),
                'total': batch.total_rows,
                'successful': batch.successful_rows,
                'failed': batch.failed_rows,
                'flagged': batch.flagged_rows,
            })
        except Exception as e:
            batch.status = 'failed'
            batch.notes = str(e)
            batch.save()
            return Response({'error': str(e)}, status=500)


class IngestUtilityView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file uploaded'}, status=400)

        try:
            tenant = get_tenant(request)
        except Tenant.DoesNotExist:
            return Response({'error': 'Tenant not found'}, status=404)

        batch = IngestionBatch.objects.create(
            tenant=tenant,
            source_type='utility_electricity',
            status='processing',
            uploaded_by=request.user,
            original_filename=file.name,
        )

        try:
            content = file.read()
            results = parse_utility_csv(content)
            _save_results(batch, results, request.user)
            batch.status = 'completed'
            batch.save()
            return Response({
                'batch_id': str(batch.id),
                'total': batch.total_rows,
                'successful': batch.successful_rows,
                'failed': batch.failed_rows,
                'flagged': batch.flagged_rows,
            })
        except Exception as e:
            batch.status = 'failed'
            batch.notes = str(e)
            batch.save()
            return Response({'error': str(e)}, status=500)


class IngestTravelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file uploaded'}, status=400)

        try:
            tenant = get_tenant(request)
        except Tenant.DoesNotExist:
            return Response({'error': 'Tenant not found'}, status=404)

        batch = IngestionBatch.objects.create(
            tenant=tenant,
            source_type='corporate_travel',
            status='processing',
            uploaded_by=request.user,
            original_filename=file.name,
        )

        try:
            content = file.read()
            fname = file.name.lower()
            if fname.endswith('.json'):
                results = parse_travel_json(content)
            else:
                results = parse_travel_csv(content)
            _save_results(batch, results, request.user)
            batch.status = 'completed'
            batch.save()
            return Response({
                'batch_id': str(batch.id),
                'total': batch.total_rows,
                'successful': batch.successful_rows,
                'failed': batch.failed_rows,
                'flagged': batch.flagged_rows,
            })
        except Exception as e:
            batch.status = 'failed'
            batch.notes = str(e)
            batch.save()
            return Response({'error': str(e)}, status=500)


def _save_results(batch, results, user):
    """Save parsed results to DB. Creates RawRecord + EmissionRecord for each row."""
    total = successful = failed = flagged = 0

    for r in results:
        total += 1
        raw = RawRecord.objects.create(
            batch=batch,
            row_index=r['row_index'],
            raw_data=r['raw_data'],
            parse_status=r.get('parse_status', 'ok'),
            parse_errors=r.get('parse_errors', []),
        )

        if r.get('parse_status') == 'error':
            failed += 1
            continue

        emit_data = {k: v for k, v in r.items()
                     if k not in ('row_index', 'raw_data', 'parse_status', 'parse_errors')}

        try:
            record = EmissionRecord.objects.create(
                tenant=batch.tenant,
                raw_record=raw,
                **emit_data,
            )
            AuditLog.objects.create(
                record=record,
                user=user,
                action='created',
                after_state={'co2e_kg': str(record.co2e_kg), 'status': record.status},
            )
            if r.get('status') == 'flagged':
                flagged += 1
            else:
                successful += 1
        except Exception as e:
            failed += 1
            raw.parse_status = 'error'
            raw.parse_errors = [str(e)]
            raw.save()

    batch.total_rows = total
    batch.successful_rows = successful
    batch.failed_rows = failed
    batch.flagged_rows = flagged
    batch.save()
