# DATA MODEL — Breathe ESG Prototype

## Core Design Principles

Every design decision flows from one constraint: **this data goes to auditors**. That means nothing is deleted, every change is recorded, and the lineage from raw source file to approved emission record must be traceable at any time.

---

## Table Overview

```
Tenant ──< TenantMembership >── User
  │
  ├──< IngestionBatch
  │         │
  │         └──< RawRecord ──── EmissionRecord >── AuditLog
  │
  └──< EmissionRecord
```

---

## Multi-Tenancy

**Table: `Tenant`**  
Every piece of data — batches, raw records, emission records — has a foreign key to `Tenant`. An analyst can only query records within tenants they are a member of (enforced in `get_queryset()` on the ViewSet).

**Table: `TenantMembership`**  
Links users to tenants with a role (analyst / admin / auditor). An auditor role is read-only and only sees `locked` records. This supports consultancies managing multiple enterprise clients.

---

## Ingestion Pipeline (Source of Truth Tracking)

**Table: `IngestionBatch`**  
One batch = one upload event. Records which user uploaded it, when, what file, and what source type. Summary stats (total/successful/failed/flagged rows) are computed at parse time. Status tracks `pending → processing → completed/failed`.

**Table: `RawRecord`**  
Stores the raw parsed row as JSON exactly as it appeared in the source file — including original column names, original values, original units. This is the source of truth. If the normalization logic had a bug, we can re-run parsing against `RawRecord` without re-uploading the file.

---

## Canonical Emission Record

**Table: `EmissionRecord`**  
One row = one normalized emission event. Key design decisions:

### Scope Classification
Assigned at parse time based on source and material type, not stored as a string but as an integer (1, 2, or 3). This makes filtering and aggregation cheaper and avoids typos.

Mapping:
- SAP fuel (diesel, petrol, LPG, natural gas) → Scope 1
- SAP procurement of unknown materials → Scope 3, Category 1
- Utility electricity → Scope 2
- Corporate travel (flights, hotels, ground) → Scope 3, Category 6

### Unit Normalization
All quantities stored in the normalized activity unit (liters for liquid fuels, kWh for electricity, km for travel, room-nights for hotels). Conversions (e.g. gallons → liters, MWh → kWh) are applied at parse time and documented in `emission_factor_source`.

### CO2e Normalization
`co2e_kg` is always in **kilograms of CO2 equivalent**. No exceptions. The field `emission_factor_used` records the factor applied, and `emission_factor_source` records where it came from (e.g. "DEFRA 2023 UK GHG Conversion Factors"). This allows auditors to verify the calculation independently.

### Audit Trail Fields
- `is_manually_edited` — set to True if an analyst edited the record after ingestion
- `edit_notes` — analyst's explanation for the edit
- `approved_by` / `approved_at` — FK to User + timestamp when approved
- `locked_at` — set when record moves to `locked`; after this point, the record is immutable at the API level

---

## Status Lifecycle

```
           [auto-flag]
ingested ──────────────> flagged ──┐
    │                              │
    └──> pending ─────────────────>┤
                                   │
                              analyst review
                                   │
                    ┌──────────────┼──────────┐
                    ▼              ▼          ▼
                approved        rejected    flagged (re-flag)
                    │
                    ▼
                 locked (for audit — immutable)
```

Records are auto-flagged at ingestion if:
- CO2e value exceeds a plausibility threshold
- Billing period exceeds 40 days (utility data)
- Unknown material type encountered (SAP data)
- Airport code not recognized (travel data)
- Distance is zero (travel data)

---

## AuditLog

Every state change on an EmissionRecord creates an `AuditLog` entry with:
- `action`: created / edited / approved / flagged / rejected / locked
- `before_state` / `after_state`: JSON snapshots of the relevant fields
- `user`: who performed the action
- `timestamp`: immutable auto-set

AuditLog rows are never deleted. They are append-only by convention (no DELETE endpoint exists in the API).

---

## Indexes

```sql
-- Most common analyst query: "show me all pending Scope 1 records for this tenant"
INDEX (tenant, scope, status)

-- Date range filtering for reporting periods
INDEX (tenant, period_start, period_end)
```

---

## What This Model Doesn't Handle (Yet)

See TRADEOFFS.md for deliberate omissions. Key ones: market-based Scope 2 accounting (RECs), multi-currency cost tracking, and GHG Protocol category sub-classification within Scope 3.
