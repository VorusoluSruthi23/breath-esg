"""
Utility Electricity Parser

Research rationale:
- We chose CSV portal export as the ingestion mode.
- Reason: Most UK/US utility providers (National Grid, EDF, Southern Company, etc.) offer
  a self-service portal where facilities managers can download interval or monthly billing data as CSV.
  PDF bills exist but require OCR and are fragile. Direct API access (e.g. Green Button standard in the US)
  requires utility-side enrollment that most enterprise clients haven't done.
- Portal CSV is realistic, reproducible, and covers 80%+ of what facilities teams actually do.

Key complexity handled:
- Billing periods don't align with calendar months (a bill might cover Dec 18 - Jan 22)
- Units vary: kWh, MWh — we normalize to kWh
- Grid emission factors vary by country/region and year
  We use UK National Grid ESO published annual average (2023): 0.20493 kg CO2e/kWh
  In production this would be location-specific (US EPA eGrid, EU AIB, etc.)

Scope: Purchased electricity = Scope 2 (market-based or location-based)
We use location-based method here; market-based would require RECs/GOs.
"""

import csv
import io
from decimal import Decimal
from datetime import datetime


# Location-based grid emission factors (kg CO2e per kWh)
# Sources: IEA 2023, UK DEFRA 2023, EPA eGrid 2022
GRID_FACTORS = {
    'GB': Decimal('0.20493'),  # UK National Grid, DEFRA 2023
    'US': Decimal('0.38600'),  # US average, EPA eGrid 2022
    'DE': Decimal('0.36600'),  # Germany, UBA 2023
    'IN': Decimal('0.71600'),  # India, CEA 2022
    'DEFAULT': Decimal('0.40000'),  # Conservative global average
}

DATE_FORMATS = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y%m%d']


def parse_date(s):
    s = str(s).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {s}")


def parse_kwh(value, unit='kWh'):
    """Normalize to kWh."""
    v = Decimal(str(value).strip().replace(',', ''))
    unit = str(unit).strip().upper()
    if unit == 'MWH':
        return v * 1000
    elif unit == 'GWH':
        return v * 1_000_000
    return v  # already kWh


def parse_utility_csv(file_content: bytes):
    """
    Expected columns (flexible mapping):
    - meter_id / Meter ID / Account Number
    - period_start / Bill From / Start Date
    - period_end / Bill To / End Date  
    - consumption / Usage (kWh) / Units Consumed
    - unit (optional, defaults to kWh)
    - country / Region (optional, for grid factor lookup)
    - site_name / Facility / Location (optional)
    """
    COLUMN_MAP = {
        'meter id': 'meter_id', 'meter_id': 'meter_id', 'account number': 'meter_id',
        'period_start': 'period_start', 'bill from': 'period_start', 'start date': 'period_start', 'from': 'period_start',
        'period_end': 'period_end', 'bill to': 'period_end', 'end date': 'period_end', 'to': 'period_end',
        'consumption': 'consumption', 'usage (kwh)': 'consumption', 'units consumed': 'consumption',
        'kwh': 'consumption', 'energy (kwh)': 'consumption',
        'unit': 'unit', 'uom': 'unit',
        'country': 'country', 'region': 'country',
        'site_name': 'site', 'facility': 'site', 'location': 'site', 'site': 'site',
        'tariff': 'tariff',
    }

    try:
        text = file_content.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = file_content.decode('latin-1')

    reader = csv.DictReader(io.StringIO(text))
    results = []

    for row_idx, raw_row in enumerate(reader):
        row = {COLUMN_MAP.get(k.strip().lower(), k.strip().lower()): v for k, v in raw_row.items()}
        flags = []

        try:
            period_start = parse_date(row.get('period_start', ''))
            period_end = parse_date(row.get('period_end', ''))

            if period_end < period_start:
                flags.append("period_end is before period_start")

            # Check for unusually long billing periods (> 40 days = likely error or 2-month bill)
            days = (period_end - period_start).days
            if days > 40:
                flags.append(f"Billing period is {days} days — spans more than one month, verify this is a single bill")

            consumption_raw = row.get('consumption', '0')
            unit_raw = row.get('unit', 'kWh')
            kwh = parse_kwh(consumption_raw, unit_raw)

            country = str(row.get('country', 'DEFAULT')).strip().upper()[:2]
            ef = GRID_FACTORS.get(country, GRID_FACTORS['DEFAULT'])
            if country not in GRID_FACTORS:
                flags.append(f"No grid factor for country '{country}' — using global average 0.4 kg/kWh")
                country = 'DEFAULT'

            co2e_kg = kwh * ef

            if kwh <= 0:
                flags.append("Zero or negative consumption — verify meter reading")
            if kwh > 1_000_000:
                flags.append(f"Very high consumption {kwh} kWh — verify this is not a data entry error")

            results.append({
                'row_index': row_idx,
                'raw_data': raw_row,
                'parse_status': 'warning' if flags else 'ok',
                'parse_errors': flags,
                'scope': 2,
                'category': 'purchased_electricity',
                'source_type': 'utility_electricity',
                'activity_value': kwh,
                'activity_unit': 'kWh',
                'activity_description': f"Meter {row.get('meter_id', 'unknown')} — {row.get('site', '')}",
                'period_start': period_start,
                'period_end': period_end,
                'facility_or_location': row.get('site', ''),
                'country': country if country != 'DEFAULT' else '',
                'co2e_kg': co2e_kg,
                'emission_factor_used': ef,
                'emission_factor_source': f"Grid factor {country}: IEA/DEFRA/EPA 2023",
                'flag_reason': '; '.join(flags),
                'status': 'flagged' if flags else 'pending',
            })

        except Exception as e:
            results.append({
                'row_index': row_idx,
                'raw_data': raw_row,
                'parse_status': 'error',
                'parse_errors': [str(e)],
            })

    return results
