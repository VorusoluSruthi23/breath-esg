# DECISIONS — Every Ambiguity Resolved

## SAP Integration

**Q: Which SAP export format?**  
A: Flat-file CSV (ALV grid export / spreadsheet download). Chose this over IDoc, OData, or BAPI because:
- IDoc requires SAP system access and an EDI partner profile — we don't have that as a third party
- OData/BAPI requires direct RFC connectivity into the client's SAP system, which involves IT firewall changes and months of procurement
- ALV grid export is how sustainability leads actually get data today: they run a procurement or goods movement report (MB52 for stock, ME2M for purchase orders, or a custom Z-report) and hit "Export to Local File"
- The downside: it's manual and error-prone. We accept this for the prototype and note it in TRADEOFFS.md

**Q: Which SAP data — fuel, procurement, or both?**  
A: Fuel and basic procurement. We handle fuel types (diesel, petrol, natural gas, LPG) as Scope 1 and unknown materials as Scope 3 Category 1 (purchased goods). We explicitly do not handle capital goods, upstream transport, or waste because those require spend-based or supplier-specific emission factors we don't have.

**Q: How to handle German column headers?**  
A: Maintain a COLUMN_MAP dictionary that maps common German SAP header names (Menge, Werk, Buchungsdatum, Einheit, Materialbeschreibung) to our internal names. This handles the most common case. Truly customized Z-reports with arbitrary headers would fail — that's in TRADEOFFS.md.

**Q: German decimal format (1.234,56 vs 1,234.56)?**  
A: Detect format by checking which separator (`.` or `,`) appears first in the string. If `.` appears before `,`, it's German (thousands.decimal) and we swap. This heuristic works for the common case but can fail on exact integers like "1.000" — flagged as a known edge case.

---

## Utility Electricity

**Q: PDF bill, portal CSV, or API?**  
A: Portal CSV. PDF bills require OCR (fragile, expensive, out of scope for 4-day prototype). Direct API (Green Button in the US, or utility-specific APIs) requires enrollment that most clients haven't done. Portal CSV is the realistic workflow: facilities manager logs into the utility portal monthly, downloads the billing export, hands it to the sustainability team.

**Q: Location-based vs. market-based Scope 2?**  
A: Location-based only. Market-based requires renewable energy certificate (REC) or Guarantee of Origin (GO) data, which is a separate procurement system. Most companies start with location-based. See TRADEOFFS.md.

**Q: Which grid emission factors?**  
A: Published annual averages from DEFRA 2023 (UK), EPA eGrid 2022 (US), UBA 2023 (Germany), CEA 2022 (India). These are the most commonly cited in GHG Protocol-compliant disclosures. In production, you'd want monthly or time-of-use factors. We default to a conservative global average (0.4 kg/kWh) for unknown countries and flag the record.

**Q: Billing periods that span two months?**  
A: We store `period_start` and `period_end` as separate dates and auto-flag any period > 40 days. We do not prorate the consumption across months — that would require assumptions about when exactly usage occurred. The analyst decides whether to split it manually.

---

## Corporate Travel

**Q: Concur API vs. Navan API vs. CSV export?**  
A: JSON (API-shaped) + CSV (export-shaped), both supported. Concur's v4 Travel API and Navan's API both return JSON with similar fields (trip type, origin, destination, cabin class, dates). We accept that JSON shape. For companies that can't set up OAuth, we also accept CSV with equivalent columns.

**Q: What if only airport codes are given, not distances?**  
A: Compute great-circle distance (haversine formula) from a lookup table of ~25 major hub airports. This is exactly what DEFRA and ICAO recommend when distance data isn't available. Known limitation: we only have major hubs; obscure regional airports will error and get flagged. In production, use a full airport database (OurAirports.com data is open-source, ~50k airports).

**Q: Radiative forcing for aviation?**  
A: Included. DEFRA 2023 aviation factors already incorporate a radiative forcing index (RFI) of approximately 1.9x for contrail and non-CO2 effects. This is the recommended approach in the UK's GHG reporting guidance and GHG Protocol. Some companies report with and without RFI — we use with, and document it in `emission_factor_source`.

**Q: What haul length threshold for short vs. long haul?**  
A: 3,700 km (consistent with DEFRA 2023 methodology). Short-haul routes like LHR-CDG use the short-haul factor; intercontinental routes use long-haul.

---

## General Architecture

**Q: Django REST + React or something simpler?**  
A: Assignment specifies Django REST + React. Within that constraint, we chose Django's built-in ORM (no Celery, no Redis) to keep deployment simple. Ingestion is synchronous — for large files (>10k rows) you'd want async processing, see TRADEOFFS.md.

**Q: Token auth vs. session auth vs. JWT?**  
A: DRF Token auth. JWT would be better for production (expiry, stateless) but Token auth is simpler, built into DRF, and sufficient for a prototype. One decision to revisit.

**Q: SQLite vs. PostgreSQL?**  
A: PostgreSQL in production (configured via DATABASE_URL env var). SQLite for local development. The settings.py auto-detects via `dj_database_url`. JSONField works differently in SQLite — we test with Postgres.

---

## Questions I'd Ask the PM

1. **Reporting period**: Do clients report on a calendar year, financial year, or rolling 12 months? This affects how we aggregate and present the dashboard.
2. **Market-based Scope 2**: Do any clients have RECs or PPAs? If so, market-based accounting is a must-have, not optional.
3. **Audit lock workflow**: Who triggers the lock — the analyst, their manager, or Breathe ESG staff? Is there an approval chain before lock?
4. **Re-ingestion**: If a client re-uploads corrected data for a period that already has approved records, what happens? Do we version, replace, or flag for manual reconciliation?
5. **Scope 3 categories**: The PM said "procurement data from SAP" — do they mean purchased goods (Cat 1) only, or also capital goods (Cat 2), upstream transport (Cat 4)? Those need different emission factors.
6. **Multi-currency**: Do we need to store monetary amounts alongside activity data? Spend-based emission factors require this.
