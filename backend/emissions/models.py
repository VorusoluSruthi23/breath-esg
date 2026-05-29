"""
EMISSIONS MODELS — The core data model for Breathe ESG

Design philosophy:
- Every row of data has ONE canonical representation in EmissionRecord
- We track where it came from (IngestionBatch → RawRecord → EmissionRecord)
- Scope 1/2/3 is assigned at ingestion time based on source type
- All quantities are normalized to kg CO2e at save time
- Nothing is ever deleted — rows are flagged, not removed (audit requirement)
"""

import uuid
from django.db import models
from django.contrib.auth.models import User


class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class TenantMembership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=50, choices=[
        ('analyst', 'Analyst'),
        ('admin', 'Admin'),
        ('auditor', 'Auditor'),
    ], default='analyst')

    class Meta:
        unique_together = ('user', 'tenant')


class IngestionBatch(models.Model):
    SOURCE_TYPES = [
        ('sap_fuel', 'SAP Fuel & Procurement'),
        ('utility_electricity', 'Utility Electricity'),
        ('corporate_travel', 'Corporate Travel'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='batches')
    source_type = models.CharField(max_length=50, choices=SOURCE_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    original_filename = models.CharField(max_length=255, blank=True)
    file_path = models.CharField(max_length=500, blank=True)
    total_rows = models.IntegerField(default=0)
    successful_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)
    flagged_rows = models.IntegerField(default=0)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.tenant.name} | {self.source_type} | {self.uploaded_at.date()}"


class RawRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name='raw_records')
    row_index = models.IntegerField()
    raw_data = models.JSONField()
    parse_status = models.CharField(max_length=20, choices=[
        ('ok', 'Parsed OK'),
        ('error', 'Parse Error'),
        ('warning', 'Parsed with Warnings'),
    ], default='ok')
    parse_errors = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['batch', 'row_index']


class EmissionRecord(models.Model):
    SCOPE_CHOICES = [
        (1, 'Scope 1'),
        (2, 'Scope 2'),
        (3, 'Scope 3'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('flagged', 'Flagged'),
        ('approved', 'Approved'),
        ('locked', 'Locked for Audit'),
        ('rejected', 'Rejected'),
    ]
    CATEGORY_CHOICES = [
        ('stationary_combustion', 'Stationary Combustion'),
        ('mobile_combustion', 'Mobile Combustion'),
        ('purchased_electricity', 'Purchased Electricity'),
        ('business_travel_air', 'Business Travel — Air'),
        ('business_travel_ground', 'Business Travel — Ground'),
        ('business_travel_hotel', 'Business Travel — Hotel'),
        ('purchased_goods', 'Purchased Goods & Services'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='emission_records')
    raw_record = models.OneToOneField(RawRecord, on_delete=models.SET_NULL, null=True, related_name='emission')
    scope = models.IntegerField(choices=SCOPE_CHOICES)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    source_type = models.CharField(max_length=50)
    activity_value = models.DecimalField(max_digits=18, decimal_places=4)
    activity_unit = models.CharField(max_length=50)
    activity_description = models.CharField(max_length=500, blank=True)
    period_start = models.DateField()
    period_end = models.DateField()
    facility_or_location = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=2, blank=True)
    co2e_kg = models.DecimalField(max_digits=18, decimal_places=4)
    emission_factor_used = models.DecimalField(max_digits=18, decimal_places=6, null=True)
    emission_factor_source = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    flag_reason = models.TextField(blank=True)
    is_manually_edited = models.BooleanField(default=False)
    edit_notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_records')
    approved_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-period_start']
        indexes = [
            models.Index(fields=['tenant', 'scope', 'status']),
            models.Index(fields=['tenant', 'period_start', 'period_end']),
        ]

    def __str__(self):
        return f"{self.tenant.slug} | Scope {self.scope} | {self.co2e_kg} kg CO2e"


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record = models.ForeignKey(EmissionRecord, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50, choices=[
        ('created', 'Created'),
        ('edited', 'Edited'),
        ('approved', 'Approved'),
        ('flagged', 'Flagged'),
        ('rejected', 'Rejected'),
        ('locked', 'Locked'),
    ])
    timestamp = models.DateTimeField(auto_now_add=True)
    before_state = models.JSONField(null=True, blank=True)
    after_state = models.JSONField(null=True, blank=True)
    notes = models.TextField(blank=True)
