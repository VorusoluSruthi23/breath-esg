# SOURCES — Research on Each Data Source

## 1. SAP Fuel & Procurement

### What real-world format we researched
SAP exposes data in several ways: IDoc (EDI flat files for system-to-system exchange), OData services (modern REST-like API layer over S/4HANA), BAPIs (legacy function call interface), and ALV Grid exports (GUI-driven spreadsheet download).

We reviewed SAP's official documentation on MM (Materials Management) module reports, specifically:
- **MB52**: Warehouse stocks of material — shows material quantities per plant/storage location
- **ME2M**: Purchase orders by material — shows procurement with vendor, quantity, unit, plant
- **MB51**: Material document list — shows goods movements including fuel receipts

We also reviewed what a real SAP export looks like from multiple publicly available SAP training screenshots and consulting firm write-ups, noting:
- Column headers vary by SAP client configuration and language settings
- German installations use: `Werk` (plant), `Menge` (quantity), `Einheit` (unit of measure), `Buchungsdatum` (posting date), `Materialbeschreibung` (material description)
- Quantity formats follow German locale: `.` as thousands separator, `,` as decimal (e.g., `1.234,56` = 1234.56)
- Date format is typically `DD.MM.YYYY` in German systems, `YYYYMMDD` in some report outputs

### What we learned
The most common path for a sustainability team to get SAP fuel data is NOT through an API — it's through a monthly manual export run by someone in finance or procurement who has SAP access. They run a report, export to CSV/XLSX, and email it or drop it in SharePoint. This is why we chose flat-file CSV as our ingestion mode.

OData would be cleaner but requires: (a) the client's SAP to have the OData service enabled, (b) a technical RFC user account, (c) VPN or S/4HANA Cloud API access. None of these can be assumed.

### What our sample data looks like and why
`sap_fuel_export.csv` uses German-format headers and includes:
- A German decimal-format quantity (`8.500` for 8500 — realistic for large fuel deliveries)
- A German material description (`Dieselkraftstoff`, `Benzin`)  
- A plant code (`DE01`, `UK02`, `IN03`) — realistic multi-plant enterprise
- An unknown material (`MATNR-9921`) — triggers our Scope 3 fallback and auto-flag
- Mixed units (L, KG, KL) — tests our unit normalization logic

### What would break in a real deployment
1. **Arbitrary Z-report headers**: Clients with custom SAP reports will have completely different column names. Our COLUMN_MAP covers common cases but can't cover all custom variants. We'd need a column-mapping UI where the analyst maps "their" headers to our fields on first upload.
2. **Plant code lookup**: Our parser stores plant codes as strings. Without a plant master lookup table (from the client's SAP configuration), we can't know which plant is in which country — so we can't apply country-specific emission factors automatically.
3. **Material number (MATNR) vs. description**: Clients often configure SAP to export only the material number, not the description. `MATNR-9921` means nothing to us. We'd need either the client's material master (another export) or a spend-based emission factor approach using the purchase amount.
4. **Multi-currency amounts**: SAP stores costs in the local currency and a global currency. We store the amount field but don't use it for emissions calculation. Spend-based Scope 3 would require this.

---

## 2. Utility Electricity

### What real-world format we researched
We reviewed how major utility providers expose consumption data:
- **UK**: National Grid ESO, EDF Energy, British Gas — all offer business portal downloads as CSV with billing period, meter ID, and kWh consumed
- **US**: Green Button standard (NAESB REQ.21) — XML or CSV with interval data (15-min or hourly); portal exports are typically monthly summary CSV
- **India**: Most state DISCOMs (BESCOM, TATA Power, Adani Electricity) offer PDF bills and basic portal exports; API access is rare
- **Germany**: Various utilities via SMGW (Smart Meter Gateway) — structured data but not standardized across providers

We also reviewed DEFRA's guidance on Scope 2 reporting and the IEA's methodology for grid emission factors.

### What we learned
Portal CSV is the universal lowest common denominator. It's available everywhere, requires no technical setup, and is what facilities managers actually use. The key complexity is:
1. **Billing periods are not calendar months**: A bill issued on January 22 might cover December 18 – January 22. Our model stores `period_start` and `period_end` separately for this reason.
2. **Multiple meters per facility**: Large buildings have separate meters for HVAC, lighting, and server rooms. Our model handles this via `meter_id` and `facility_or_location`.
3. **Grid factors change annually**: We use 2023 factors. In production, the factor should be selected based on `period_end` year, not the upload date.

### What our sample data looks like and why
`utility_electricity.csv` includes:
- `MTR-002`: Billing period Dec 18 – Jan 22 (35 days) — triggers the multi-month flag
- `MTR-003`: Delhi office with Indian grid factor (0.716 kg/kWh vs UK 0.205) — shows why country matters enormously for Scope 2
- `MTR-004`: US office — tests EPA eGrid factor
- Two entries for `MTR-001`: January and February London HQ — tests that duplicate meter-period combinations are possible and expected (not an error)

### What would break in a real deployment
1. **Country detection**: We use a `country` column that clients may not include. Without it, we fall back to the global average and flag. A better approach: link meter IDs to a site master record that stores country.
2. **Sub-annual grid factors**: Some jurisdictions (UK, parts of US) publish monthly or seasonal grid factors. Using annual averages introduces error.
3. **Reactive vs. active power**: Some utility exports include reactive power (kVAR) alongside active (kWh). We only use kWh; parsing a file that doesn't clearly separate them would compute wrong totals.
4. **Multi-site clients with 500+ meters**: Uploading a CSV with 500 rows synchronously is still fine, but the UI would need pagination and filtering by meter/site to be usable.

---

## 3. Corporate Travel

### What real-world format we researched
We reviewed:
- **Concur Travel API v4** (SAP Concur developer documentation): Returns trip itineraries as JSON with segments. Each segment has type, carrier, origin, destination, cabin class, departure datetime.
- **Navan (formerly TripActions) API**: Similar structure, JSON-based, segments per booking with airport codes and cabin class.
- **TMC (Travel Management Company) exports**: Amex GBT, BCD Travel, and CWT all offer periodic CSV exports to the corporate travel manager. Fields typically include: traveler name, trip date, origin, destination, mode, cabin, fare basis, cost.

We also reviewed DEFRA 2023 methodology for business travel emission factors (document: "UK Government GHG Conversion Factors for Company Reporting"), specifically:
- Aviation: factors by haul type (short/long, threshold 3,700 km) and cabin class, including radiative forcing
- Ground: factors by mode per km
- Hotels: factor per room-night by geography

### What we learned
Distance is the key variable for flights, and it's often not in the export. Concur gives you airport codes; you have to compute distance yourself. DEFRA explicitly recommends the haversine great-circle formula for this. We implemented this with a lookup table of 24 major hub airports — sufficient for the prototype but not for a client with staff flying through Chittagong or Kigali.

The radiative forcing debate is real: some companies include it (DEFRA recommends), some exclude it (allows lower-looking numbers). We include it and document it clearly per `emission_factor_source`.

### What our sample data looks like and why
`corporate_travel.json` uses a Navan-shaped JSON format with:
- A long-haul economy flight LHR→JFK — tests haversine distance, long-haul factor
- A hotel stay in New York — tests room-night calculation
- A taxi from JFK — tests ground transport
- A business-class flight LHR→DXB→BLR (two segments, multi-leg) — tests that each flight segment is treated independently (as it should be — you can't combine segments for distance)
- A hotel in Bengaluru — tests that the same hotel factor applies globally (we don't have region-specific hotel factors yet; that's a TRADEOFF)

### What would break in a real deployment
1. **Unknown airport codes**: Our lookup covers 24 airports. Any departure/arrival outside that set (regional airports, secondary hubs) will fail and be flagged. Fix: integrate OurAirports database (~50,000 airports, open-source).
2. **Multi-leg trips and layovers**: Our parser treats each JSON object as one segment. If Concur exports a trip as one record with origin=LHR and destination=BLR (ignoring the DXB connection), we'd compute the direct great-circle distance, which is wrong. Fix: require segment-level data.
3. **Personal vs. business travel**: If the company uses a travel platform for both personal and expensed travel, the export may include non-business trips. We have no way to detect this without additional metadata (trip purpose, expense category).
4. **Uber/Lyft API**: Ground transport data is often missing entirely — employees expense receipts but don't log distances. We can only compute emissions if distance is known.
