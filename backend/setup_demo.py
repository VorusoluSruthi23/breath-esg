"""
Run this script to seed demo data: tenant, analyst user, and sample emission records.
Usage: python manage.py shell < setup_demo.py
       OR: python setup_demo.py (if run from project root)
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'breathe_esg.settings')
django.setup()

from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from emissions.models import Tenant, TenantMembership, IngestionBatch, RawRecord, EmissionRecord, AuditLog
from datetime import date
from decimal import Decimal

# Create tenant
tenant, _ = Tenant.objects.get_or_create(name='Acme Corp', slug='acme-corp')
print(f"Tenant: {tenant.name}")

# Create analyst user
user, created = User.objects.get_or_create(username='analyst')
if created:
    user.set_password('demo1234')
    user.first_name = 'Priya'
    user.last_name = 'Sharma'
    user.save()
token, _ = Token.objects.get_or_create(user=user)
print(f"User: analyst / demo1234 | Token: {token.key}")

# Admin user
admin, created = User.objects.get_or_create(username='admin', is_superuser=True, is_staff=True)
if created:
    admin.set_password('admin1234')
    admin.save()
Token.objects.get_or_create(user=admin)

# Memberships
TenantMembership.objects.get_or_create(user=user, tenant=tenant, defaults={'role': 'analyst'})
TenantMembership.objects.get_or_create(user=admin, tenant=tenant, defaults={'role': 'admin'})

# Create a batch and records for each source type
def make_batch(source_type, filename):
    return IngestionBatch.objects.create(
        tenant=tenant, source_type=source_type, status='completed',
        uploaded_by=user, original_filename=filename,
        total_rows=3, successful_rows=2, failed_rows=0, flagged_rows=1,
    )

# SAP records
sap_batch = make_batch('sap_fuel', 'sap_export_q1_2024.csv')
sap_records = [
    dict(scope=1, category='mobile_combustion', source_type='sap_fuel',
         activity_value=Decimal('5000'), activity_unit='liters',
         activity_description='Diesel @ Plant DE01', period_start=date(2024,1,1), period_end=date(2024,1,31),
         facility_or_location='DE01', country='DE', co2e_kg=Decimal('12594.5'),
         emission_factor_used=Decimal('2.5189'), emission_factor_source='DEFRA 2023',
         status='pending', flag_reason=''),
    dict(scope=1, category='stationary_combustion', source_type='sap_fuel',
         activity_value=Decimal('2000'), activity_unit='kg',
         activity_description='Natural Gas @ Plant UK02', period_start=date(2024,1,1), period_end=date(2024,1,31),
         facility_or_location='UK02', country='GB', co2e_kg=Decimal('4044.0'),
         emission_factor_used=Decimal('2.022'), emission_factor_source='DEFRA 2023',
         status='flagged', flag_reason='Unusually high emission: verify quantity'),
    dict(scope=3, category='purchased_goods', source_type='sap_fuel',
         activity_value=Decimal('500'), activity_unit='units',
         activity_description='Unknown material MATNR-9921', period_start=date(2024,2,1), period_end=date(2024,2,28),
         facility_or_location='UK02', country='GB', co2e_kg=Decimal('500.0'),
         emission_factor_used=Decimal('1.0'), emission_factor_source='DEFRA 2023 default',
         status='pending', flag_reason="Unknown material — defaulted to Scope 3"),
]

# Utility records
util_batch = make_batch('utility_electricity', 'utility_portal_q1_2024.csv')
util_records = [
    dict(scope=2, category='purchased_electricity', source_type='utility_electricity',
         activity_value=Decimal('48000'), activity_unit='kWh',
         activity_description='Meter MTR-001 — London HQ', period_start=date(2024,1,1), period_end=date(2024,1,31),
         facility_or_location='London HQ', country='GB', co2e_kg=Decimal('9836.64'),
         emission_factor_used=Decimal('0.20493'), emission_factor_source='DEFRA 2023 UK Grid',
         status='approved', flag_reason=''),
    dict(scope=2, category='purchased_electricity', source_type='utility_electricity',
         activity_value=Decimal('62000'), activity_unit='kWh',
         activity_description='Meter MTR-002 — Manchester Warehouse',
         period_start=date(2023,12,18), period_end=date(2024,1,22),
         facility_or_location='Manchester Warehouse', country='GB', co2e_kg=Decimal('12705.66'),
         emission_factor_used=Decimal('0.20493'), emission_factor_source='DEFRA 2023 UK Grid',
         status='flagged', flag_reason='Billing period is 35 days — spans more than one month'),
    dict(scope=2, category='purchased_electricity', source_type='utility_electricity',
         activity_value=Decimal('35000'), activity_unit='kWh',
         activity_description='Meter MTR-003 — Delhi Office',
         period_start=date(2024,2,1), period_end=date(2024,2,29),
         facility_or_location='Delhi Office', country='IN', co2e_kg=Decimal('25060.0'),
         emission_factor_used=Decimal('0.716'), emission_factor_source='CEA India 2022',
         status='pending', flag_reason=''),
]

# Travel records
travel_batch = make_batch('corporate_travel', 'navan_export_q1_2024.json')
travel_records = [
    dict(scope=3, category='business_travel_air', source_type='corporate_travel',
         activity_value=Decimal('5541'), activity_unit='km',
         activity_description='Flight LHR→JFK (economy, long-haul)',
         period_start=date(2024,1,15), period_end=date(2024,1,15),
         facility_or_location='LHR→JFK', country='', co2e_kg=Decimal('1057.5'),
         emission_factor_used=Decimal('0.19085'), emission_factor_source='DEFRA 2023 long-haul economy with RF',
         status='pending', flag_reason=''),
    dict(scope=3, category='business_travel_hotel', source_type='corporate_travel',
         activity_value=Decimal('3'), activity_unit='room-nights',
         activity_description='Hotel — Marriott Midtown New York',
         period_start=date(2024,1,15), period_end=date(2024,1,18),
         facility_or_location='New York', country='US', co2e_kg=Decimal('62.4'),
         emission_factor_used=Decimal('20.8'), emission_factor_source='DEFRA 2023 hotel room-night',
         status='approved', flag_reason=''),
    dict(scope=3, category='business_travel_ground', source_type='corporate_travel',
         activity_value=Decimal('45'), activity_unit='km',
         activity_description='Taxi — JFK Airport to Midtown Manhattan',
         period_start=date(2024,1,15), period_end=date(2024,1,15),
         facility_or_location='New York', country='US', co2e_kg=Decimal('9.17'),
         emission_factor_used=Decimal('0.20369'), emission_factor_source='DEFRA 2023 taxi per km',
         status='pending', flag_reason=''),
]

for records, batch in [(sap_records, sap_batch), (util_records, util_batch), (travel_records, travel_batch)]:
    for r in records:
        raw = RawRecord.objects.create(batch=batch, row_index=0, raw_data={k: str(v) for k, v in r.items()}, parse_status='ok')
        em = EmissionRecord.objects.create(tenant=tenant, raw_record=raw, **r)
        AuditLog.objects.create(record=em, user=user, action='created',
                                after_state={'co2e_kg': str(em.co2e_kg), 'status': em.status})

print(f"\nSeed complete!")
print(f"Login: analyst / demo1234")
print(f"Admin: admin / admin1234")
print(f"Tenant: acme-corp")
print(f"Records: {EmissionRecord.objects.count()} emission records")
