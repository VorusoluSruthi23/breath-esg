# TRADEOFFS — Three Things Deliberately Not Built

## 1. Asynchronous Ingestion Pipeline

**What we built:** Synchronous file upload — when you POST a file, the server parses it, writes all records to the database, and returns the result in the same HTTP request.

**What we didn't build:** A proper async pipeline with a task queue (Celery + Redis or Django-Q), background workers, and a polling endpoint to check job status.

**Why we left it out:**  
For the prototype with sample files of 5–20 rows, synchronous ingestion is fine. A production SAP export or utility portal dump could have 50,000 rows. A synchronous request handling that would time out at 30 seconds on most hosting platforms and would block a gunicorn worker for the entire duration, starving other requests.

**What we'd build instead:**  
On upload, create the `IngestionBatch` record immediately and return a `batch_id`. The actual parsing runs in a Celery task. The frontend polls `GET /api/batches/{id}/` until `status == completed`. This also lets us handle partial failures gracefully — rows can be inserted as they're parsed rather than all-or-nothing.

**Why this is the right tradeoff for now:** Deploying Celery + Redis adds two more services, more infrastructure config, and at least a day of work. For a 4-day prototype reviewed by analysts, synchronous is fine as long as sample files are small.

---

## 2. Market-Based Scope 2 Accounting

**What we built:** Location-based Scope 2 — we use the grid average emission factor for the country where electricity is consumed.

**What we didn't build:** Market-based Scope 2 — where a company's actual contracted electricity supply determines the emission factor. This requires tracking renewable energy certificates (RECs in the US), Guarantees of Origin (GOs in Europe), or Power Purchase Agreements (PPAs), each of which has its own data format, validity period, and verification process.

**Why we left it out:**  
Market-based Scope 2 is a separate data ingestion problem. You'd need a new source type for REC/GO purchases, a matching engine to pair certificates with consumption, and logic to handle certificate vintages and geographies. It's at least as complex as the three sources we already built.

**What we'd build instead:**  
A `RenewableEnergyCertificate` model linked to `Tenant`, covering a period, a quantity of MWh, and a certificate type/registry. The Scope 2 calculator would check whether consumption in a given period and location is covered by a valid certificate before applying the residual mix factor.

**Why this matters:** Many enterprise clients with renewable energy commitments (RE100 signatories, SBTi targets) require market-based Scope 2 to report net-zero progress. A platform that can't do market-based will lose these clients. It should be in v2.

---

## 3. Role-Based Data Editing and Approval Chains

**What we built:** Any authenticated analyst can approve, reject, or flag any record in their tenant. One person can both flag and approve. There is no multi-person approval workflow.

**What we didn't build:** A proper RBAC system with approval chains — for example: an analyst flags → a senior analyst reviews → a sustainability manager gives final approval → records lock. Or: any edit to a locked record requires two-person authorization.

**Why we left it out:**  
Approval workflows are highly client-specific. One company might require: analyst approves → external auditor spot-checks → CFO signs off. Another might have a simple: analyst reviews → auto-locks at quarter end. Building a generic workflow engine (like a state machine with configurable transitions and role requirements) is a multi-week project that would dominate the prototype timeline.

**What we'd build instead:**  
A `WorkflowConfig` model per tenant that defines: required roles at each approval stage, whether edits require a second reviewer, and automatic lock triggers (e.g., "lock all approved records on the 5th of the month following the reporting period"). The `EmissionRecord` status transitions would check `WorkflowConfig` before allowing state changes.

**Why this matters:** In real GHG audits (ISO 14064, CDP reporting), the chain of custody from raw data to reported figure must be documented and defensible. A single-person approval is often insufficient for materiality reasons. This is a must-have before going to enterprise clients with Big 4 auditors.
