from rest_framework import serializers
from .models import EmissionRecord, IngestionBatch, AuditLog, Tenant


class EmissionRecordSerializer(serializers.ModelSerializer):
    scope_display = serializers.CharField(source='get_scope_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    approved_by_name = serializers.SerializerMethodField()

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return obj.approved_by.get_full_name() or obj.approved_by.username
        return None

    class Meta:
        model = EmissionRecord
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'raw_record', 'created_at', 'locked_at']


class IngestionBatchSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()

    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return obj.uploaded_by.username
        return None

    class Meta:
        model = IngestionBatch
        fields = '__all__'


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    def get_user_name(self, obj):
        return obj.user.username if obj.user else None

    class Meta:
        model = AuditLog
        fields = '__all__'


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'slug']
