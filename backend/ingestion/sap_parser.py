"""
SAP Fuel & Procurement Parser

Research rationale (for SOURCES.md defense):
- SAP exports come in several forms. We chose the flat-file format (IDoc flatfile / ALV grid export)
  because it's the most common way non-technical sustainability leads actually GET data out of SAP:
  they run a report (MB52, ME2M, or a custom Z-report), hit "Export to Spreadsheet", and get a CSV/XLSX.
- OData/BAPI would require direct SAP system access we won't have as a third-party.
- Real SAP exports have: German column headers (Menge=quantity, Werk=plant, Matnr=material),
  inconsistent decimal separators (1.234,56 instead of 1,234.56), plant codes like 'DE01' that
  need lookup, and dates as YYYYMMDD or DD.MM.YYYY.

Scope assignment:
- Fuel (diesel, petrol, natural gas) = Scope 1 (direct combustion)
- Procurement of goods = Scope 3, category 1 (purchased goods & services)

Emission factors: DEFRA 2023 UK Government GHG Conversion Factors (publicly available)
"""

import csv
import io
from decimal import Decimal, InvalidOperation
from datetime import datetime


# Emission factors in kg CO2e per unit
# Source: DEFRA 2023 GHG Conversion Factors
EMISSION_FACTORS = {
    'diesel':       {'factor': Decimal('2.51890'), 'unit': 'liters', 'scope': 1, 'category': 'mobile_combustion'},
    'petrol':       {'factor': Decimal('2.31370'), 'unit': 'liters', 'scope': 1, 'category': 'mobile_combustion'},
    'natural_gas':  {'factor': Decimal('2.02200'), 'unit': 'kg',     'scope': 1, 'category': 'stationary_combustion'},
    'lpg':          {'factor': Decimal('1.55490'), 'unit': 'liters', 'scope': 1, 'category': 'stationary_combustion'},
    'default':      {'factor': Decimal('1.00000'), 'unit': 'units',  'scope': 3, 'category': 'purchased_goods'},
}

# Map SAP material codes / descriptions to fuel types
# Real SAP uses material numbers (MATNR) — these are illustrative but realistic
MATERIAL_MAP = {
    'diesel': 'diesel', 'dieselkraftstoff': 'diesel', 'gas oil': 'diesel',
    'petrol': 'petrol', 'benzin': 'petrol', 'gasoline': 'petrol',
    'natural gas': 'natural_gas', 'erdgas': 'natural_gas', 'ng': 'natural_gas',
    'lpg': 'lpg', 'flüssiggas': 'lpg',
}

# SAP date formats we've seen in the wild
DATE_FORMATS = ['%d.%m.%Y', '%Y%m%d', '%Y-%m-%d', '%m/%d/%Y']


def parse_sap_date(date_str):
    """Try multiple date formats — SAP exports vary by system locale."""
    date_str = str(date_str).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {date_str}")


def parse_sap_number(value_str):
    """
    SAP with German locale uses '.' as thousands separator and ',' as decimal.
    E.g. 1.234,56 means 1234.56
    """
    s = str(value_str).strip()
    # Detect German format: has comma after digits
    if ',' in s and '.' in s:
        if s.index('.') < s.index(','):  # 1.234,56 — German
            s = s.replace('.', '').replace(',', '.')
        else:  # 1,234.56 — English
            s = s.replace(',', '')
    elif ',' in s:  # Could be 1234,56 (German decimal)
        s = s.replace(',', '.')
    return Decimal(s)


def normalize_unit(unit_str, quantity):
    """
    Convert everything to our base units (liters for liquid fuels, kg for gas).
    SAP can export in multiple units: L, GAL, KG, M3, etc.
    """
    unit = str(unit_str).strip().upper()
    conversions = {
        'L': ('liters', Decimal('1')),
        'LTR': ('liters', Decimal('1')),
        'GAL': ('liters', Decimal('3.78541')),
        'KG': ('kg', Decimal('1')),
        'M3': ('kg', Decimal('0.717')),   # approximate for natural gas at STP
        'FT3': ('kg', Decimal('0.02031')),
    }
    if unit in conversions:
        norm_unit, factor = conversions[unit]
        return norm_unit, quantity * factor
    return unit_str.lower(), quantity


def parse_sap_csv(file_content: bytes, batch_id=None):
    """
    Main entry point. Accepts CSV bytes, returns list of dicts ready for EmissionRecord creation.
    
    Expected columns (we map both English and German headers):
    - Document Date / Buchungsdatum
    - Plant / Werk  
    - Material Description / Materialbeschreibung
    - Quantity / Menge
    - Unit / Einheit
    - Vendor / Lieferant (optional)
    """
    results = []
    errors = []

    # Column name aliases: SAP German → our internal name
    COLUMN_MAP = {
        'document date': 'date', 'buchungsdatum': 'date', 'posting date': 'date',
        'plant': 'plant', 'werk': 'plant',
        'material description': 'material', 'materialbeschreibung': 'material',
        'material': 'material', 'material no': 'material',
        'quantity': 'quantity', 'menge': 'quantity',
        'unit': 'unit', 'einheit': 'unit', 'uom': 'unit',
        'vendor': 'vendor', 'lieferant': 'vendor',
        'amount': 'amount', 'betrag': 'amount',
    }

    try:
        text = file_content.decode('utf-8-sig')  # utf-8-sig strips BOM from Excel exports
    except UnicodeDecodeError:
        text = file_content.decode('latin-1')   # fallback for old SAP systems

    reader = csv.DictReader(io.StringIO(text))

    # Normalize headers
    def map_header(h):
        return COLUMN_MAP.get(h.strip().lower(), h.strip().lower())

    for row_idx, raw_row in enumerate(reader):
        normalized_row = {map_header(k): v for k, v in raw_row.items()}
        row_errors = []

        try:
            # Parse date
            date = parse_sap_date(normalized_row.get('date', ''))

            # Parse quantity
            qty_raw = normalized_row.get('quantity', '0')
            quantity = parse_sap_number(qty_raw)

            # Get unit and normalize
            unit_raw = normalized_row.get('unit', 'L')
            norm_unit, norm_quantity = normalize_unit(unit_raw, quantity)

            # Identify material type for emission factor
            material_desc = str(normalized_row.get('material', '')).lower().strip()
            fuel_type = MATERIAL_MAP.get(material_desc, 'default')
            ef_data = EMISSION_FACTORS[fuel_type]

            # Calculate CO2e
            co2e_kg = norm_quantity * ef_data['factor']

            # Auto-flag suspicious values
            flags = []
            if co2e_kg > Decimal('100000'):
                flags.append(f"Unusually high emission: {co2e_kg} kg CO2e — verify quantity")
            if quantity <= 0:
                flags.append("Non-positive quantity")
            if fuel_type == 'default':
                flags.append(f"Unknown material '{material_desc}' — defaulted to Scope 3 purchased goods")

            results.append({
                'row_index': row_idx,
                'raw_data': raw_row,
                'parse_status': 'warning' if flags else 'ok',
                'parse_errors': flags,
                # EmissionRecord fields
                'scope': ef_data['scope'],
                'category': ef_data['category'],
                'source_type': 'sap_fuel',
                'activity_value': norm_quantity,
                'activity_unit': norm_unit,
                'activity_description': f"{normalized_row.get('material', '')} @ {normalized_row.get('plant', 'Unknown plant')}",
                'period_start': date,
                'period_end': date,
                'facility_or_location': normalized_row.get('plant', ''),
                'co2e_kg': co2e_kg,
                'emission_factor_used': ef_data['factor'],
                'emission_factor_source': 'DEFRA 2023 UK GHG Conversion Factors',
                'flag_reason': '; '.join(flags),
                'status': 'flagged' if flags else 'pending',
            })

        except Exception as e:
            errors.append({'row': row_idx, 'error': str(e), 'raw': dict(raw_row)})
            results.append({
                'row_index': row_idx,
                'raw_data': raw_row,
                'parse_status': 'error',
                'parse_errors': [str(e)],
            })

    return results, errors
