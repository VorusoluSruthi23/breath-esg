"""
Corporate Travel Parser

Research rationale:
- Studied Concur Travel, Navan (formerly TripActions), and SAP Concur API docs.
- Concur exposes trip data via its v4 Travel REST API — but OAuth setup requires corporate IT.
- Navan has a similar API (Navan Expense API).
- In practice, sustainability leads get this data as a CSV export from their travel management company (TMC).
- We accept JSON (closer to what an API would return) and CSV (what an export looks like).
- We handle flights, hotels, and ground transport — each has a different emission factor methodology.

Scope: Business travel = Scope 3, Category 6 (GHG Protocol)

Emission factor methodology:
- Flights: DEFRA 2023 per passenger-km, by cabin class and haul type
  Short haul (<3700 km): economy 0.15536, business 0.22896 kg CO2e/pkm
  Long haul (>=3700 km): economy 0.19085, business 0.42869 kg CO2e/pkm
  (includes radiative forcing multiplier of ~1.9x — as recommended by DEFRA for aviation)
- Hotels: DEFRA 2023 per room-night, by region: ~20.8 kg CO2e/room-night (UK average)
- Ground transport: per km, by mode

Distance calculation:
- If origin/destination are airport codes, we use a lookup table of major airport coords
  and compute great-circle distance (haversine). Not perfectly accurate but standard practice.
- If distance_km is provided directly, we use that.
"""

import json
import csv
import io
import math
from decimal import Decimal
from datetime import datetime, date


# DEFRA 2023 flight factors (kg CO2e per passenger-km, WITH radiative forcing)
FLIGHT_FACTORS = {
    ('short', 'economy'):   Decimal('0.15536'),
    ('short', 'business'):  Decimal('0.22896'),
    ('short', 'first'):     Decimal('0.22896'),
    ('long', 'economy'):    Decimal('0.19085'),
    ('long', 'business'):   Decimal('0.42869'),
    ('long', 'first'):      Decimal('0.57203'),
}

# Hotel: DEFRA 2023 UK average per room-night
HOTEL_FACTOR = Decimal('20.8')  # kg CO2e / room-night

# Ground transport per km (kg CO2e/km)
GROUND_FACTORS = {
    'taxi': Decimal('0.20369'),
    'car_rental': Decimal('0.16844'),
    'train': Decimal('0.03549'),
    'bus': Decimal('0.10279'),
    'default': Decimal('0.17'),
}

# Airport IATA code → (lat, lon) for major hubs
# In production this would be a full database of 10,000+ airports
AIRPORTS = {
    'LHR': (51.477, -0.461), 'JFK': (40.641, -73.778), 'LAX': (33.943, -118.408),
    'CDG': (49.013, 2.550), 'AMS': (52.310, 4.768), 'FRA': (50.033, 8.571),
    'DXB': (25.253, 55.365), 'SIN': (1.350, 103.994), 'NRT': (35.765, 140.386),
    'SYD': (33.946, 151.177), 'ORD': (41.978, -87.905), 'ATL': (33.641, -84.427),
    'BOM': (19.089, 72.868), 'DEL': (28.556, 77.100), 'BLR': (13.198, 77.706),
    'HKG': (22.309, 113.915), 'PEK': (40.080, 116.584), 'DFW': (32.897, -97.038),
    'MIA': (25.796, -80.287), 'SFO': (37.619, -122.375), 'BOS': (42.363, -71.005),
    'IAD': (38.944, -77.456), 'EWR': (40.690, -74.174),
}


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km between two lat/lon points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def get_flight_distance(origin, destination):
    """Return distance in km between two airport codes. Raises if unknown."""
    o = str(origin).strip().upper()
    d = str(destination).strip().upper()
    if o not in AIRPORTS:
        raise ValueError(f"Unknown origin airport: {o}")
    if d not in AIRPORTS:
        raise ValueError(f"Unknown destination airport: {d}")
    return haversine_km(*AIRPORTS[o], *AIRPORTS[d])


def classify_haul(distance_km):
    return 'short' if distance_km < 3700 else 'long'


def parse_date(s):
    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ']:
        try:
            return datetime.strptime(str(s).strip()[:19], fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {s}")


def process_trip(trip: dict, row_idx: int):
    """Process a single trip record. Returns one or more emission sub-records."""
    records = []
    flags = []

    trip_type = str(trip.get('type', trip.get('trip_type', ''))).lower().strip()
    travel_date_str = trip.get('date') or trip.get('departure_date') or trip.get('check_in_date', '')

    try:
        travel_date = parse_date(travel_date_str)
    except:
        travel_date = date.today()
        flags.append("Could not parse travel date — defaulted to today")

    # ── FLIGHT ────────────────────────────────────────────────────────────────
    if trip_type in ('flight', 'air', 'airline'):
        origin = trip.get('origin') or trip.get('from')
        destination = trip.get('destination') or trip.get('to')
        cabin = str(trip.get('cabin_class', trip.get('class', 'economy'))).lower()
        if cabin not in ('economy', 'business', 'first'):
            cabin = 'economy'

        dist_km = trip.get('distance_km')
        if dist_km:
            dist_km = float(dist_km)
        else:
            try:
                dist_km = get_flight_distance(origin, destination)
            except ValueError as e:
                flags.append(str(e))
                dist_km = 0

        haul = classify_haul(dist_km)
        factor = FLIGHT_FACTORS.get((haul, cabin), FLIGHT_FACTORS[('long', 'economy')])
        co2e_kg = Decimal(str(dist_km)) * factor

        if dist_km == 0:
            flags.append("Distance is 0 — cannot compute emissions, verify airport codes")

        records.append({
            'row_index': row_idx,
            'raw_data': trip,
            'parse_status': 'warning' if flags else 'ok',
            'parse_errors': flags,
            'scope': 3,
            'category': 'business_travel_air',
            'source_type': 'corporate_travel',
            'activity_value': Decimal(str(dist_km)),
            'activity_unit': 'km',
            'activity_description': f"Flight {origin}→{destination} ({cabin}, {haul}-haul)",
            'period_start': travel_date,
            'period_end': travel_date,
            'facility_or_location': f"{origin}→{destination}",
            'co2e_kg': co2e_kg,
            'emission_factor_used': factor,
            'emission_factor_source': f"DEFRA 2023 — {haul}-haul {cabin} with radiative forcing",
            'flag_reason': '; '.join(flags),
            'status': 'flagged' if flags else 'pending',
        })

    # ── HOTEL ─────────────────────────────────────────────────────────────────
    elif trip_type in ('hotel', 'accommodation', 'lodging'):
        check_in = parse_date(trip.get('check_in_date', travel_date_str))
        check_out = parse_date(trip.get('check_out_date', travel_date_str))
        nights = max((check_out - check_in).days, 1)
        rooms = int(trip.get('rooms', 1))
        room_nights = nights * rooms
        co2e_kg = HOTEL_FACTOR * room_nights

        records.append({
            'row_index': row_idx,
            'raw_data': trip,
            'parse_status': 'warning' if flags else 'ok',
            'parse_errors': flags,
            'scope': 3,
            'category': 'business_travel_hotel',
            'source_type': 'corporate_travel',
            'activity_value': Decimal(str(room_nights)),
            'activity_unit': 'room-nights',
            'activity_description': f"Hotel — {trip.get('hotel_name', '')} {trip.get('city', '')}",
            'period_start': check_in,
            'period_end': check_out,
            'facility_or_location': trip.get('city', ''),
            'co2e_kg': co2e_kg,
            'emission_factor_used': HOTEL_FACTOR,
            'emission_factor_source': 'DEFRA 2023 — UK average hotel room-night',
            'flag_reason': '; '.join(flags),
            'status': 'flagged' if flags else 'pending',
        })

    # ── GROUND TRANSPORT ─────────────────────────────────────────────────────
    elif trip_type in ('taxi', 'car', 'car_rental', 'train', 'bus', 'ground', 'rail'):
        dist_km = Decimal(str(trip.get('distance_km', 0)))
        mode = trip_type if trip_type in GROUND_FACTORS else 'default'
        factor = GROUND_FACTORS[mode]
        co2e_kg = dist_km * factor

        if dist_km == 0:
            flags.append("Distance is 0 km — no emissions computed")

        records.append({
            'row_index': row_idx,
            'raw_data': trip,
            'parse_status': 'warning' if flags else 'ok',
            'parse_errors': flags,
            'scope': 3,
            'category': 'business_travel_ground',
            'source_type': 'corporate_travel',
            'activity_value': dist_km,
            'activity_unit': 'km',
            'activity_description': f"{mode.replace('_', ' ').title()} — {trip.get('from', '')} to {trip.get('to', '')}",
            'period_start': travel_date,
            'period_end': travel_date,
            'facility_or_location': trip.get('city', ''),
            'co2e_kg': co2e_kg,
            'emission_factor_used': factor,
            'emission_factor_source': 'DEFRA 2023 — ground transport per km',
            'flag_reason': '; '.join(flags),
            'status': 'flagged' if flags else 'pending',
        })

    else:
        records.append({
            'row_index': row_idx,
            'raw_data': trip,
            'parse_status': 'error',
            'parse_errors': [f"Unknown trip type: '{trip_type}'"],
        })

    return records


def parse_travel_json(file_content: bytes):
    """Parse JSON array of trip records (Concur/Navan API format)."""
    data = json.loads(file_content.decode('utf-8'))
    if isinstance(data, dict) and 'trips' in data:
        data = data['trips']

    results = []
    for idx, trip in enumerate(data):
        results.extend(process_trip(trip, idx))
    return results


def parse_travel_csv(file_content: bytes):
    """Parse CSV export (what a TMC would provide)."""
    text = file_content.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text))
    COLUMN_MAP = {
        'trip type': 'type', 'type': 'type', 'category': 'type',
        'departure date': 'date', 'date': 'date', 'travel date': 'date',
        'origin': 'origin', 'from': 'origin', 'departure': 'origin',
        'destination': 'destination', 'to': 'destination', 'arrival': 'destination',
        'cabin class': 'cabin_class', 'class': 'cabin_class',
        'distance (km)': 'distance_km', 'distance_km': 'distance_km',
        'check-in date': 'check_in_date', 'check in': 'check_in_date',
        'check-out date': 'check_out_date', 'check out': 'check_out_date',
        'hotel name': 'hotel_name', 'property': 'hotel_name',
        'city': 'city', 'location': 'city',
        'rooms': 'rooms',
        'employee': 'employee', 'traveler': 'employee',
    }
    results = []
    for idx, raw_row in enumerate(reader):
        trip = {COLUMN_MAP.get(k.strip().lower(), k.strip().lower()): v for k, v in raw_row.items()}
        results.extend(process_trip(trip, idx))
    return results
