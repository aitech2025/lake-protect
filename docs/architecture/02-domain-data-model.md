# 02 — Domain and Data Model

## 1. Authority and provenance
Each imported record carries source, authority class, effective date, retrieval date, validation status and permitted use. Distinguish:
- authoritative departmental record;
- certified/notified boundary;
- derived geometry (digitised, transformed, buffered or inferred);
- external reference data;
- field observation;
- model output.

OSM or other open-map geometry can help discover assets but must never be represented as an official boundary. Department systems remain authoritative. Data-sharing agreements define refresh, correction, retention, access and redistribution.

## 2. Stable asset identity
Create a permanent platform UUID independent of department codes, survey numbers, GIS IDs and portal identifiers. An asset can span multiple parcels; a parcel can intersect multiple assets; custodian and enforcement authority can differ.

Administrative hierarchy: State → District → Mandal / Urban Local Body → Village / Ward → Asset. Administrative units and asset links need effective dates because boundaries and responsibilities change.

## 3. Logical entities
| Entity | Purpose |
|---|---|
| public_assets | Stable asset identity, category, status, geometry, baseline |
| asset_categories | Category-specific metadata and rule-pack configuration |
| administrative_units | Effective-dated state/district/mandal/ULB/village/ward hierarchy |
| asset_admin_links | Temporal asset-to-administration relationships |
| land_parcels | Survey number, subdivision, village, classification, source reference |
| asset_parcels | Many-to-many asset/parcel links and overlap area |
| asset_boundaries | Immutable geometry versions, kind, status, dates and supersession |
| boundary_sources | Notifications, orders, survey records and source documents |
| departments | Configurable department and agency directory |
| jurisdictions | Effective-dated remit and geographic extent |
| asset_responsibilities | Custodian, owner, jurisdiction, operational and enforcement relationships |
| observations | Acquired source observations, sensor, time, quality and provenance |
| processing_runs | Pipeline version, configuration hash, input/output references and status |
| change_candidates | Candidate geometry, class, observation bracket, confidence and run |
| candidate_asset_links | Spatial match to assets, parcels and exact boundary version |
| legal_references | Permits, notifications, works, court matters and disputes |
| candidate_legal_checks | Rule result, flags, boundary version and rule version |
| alerts / cases | Operational work item and formal case/action record |
| field_verifications | Officer, time, location, outcome and attachments |
| evidence_objects | Immutable object metadata, hash, source and retention |
| audit_events | Append-only actor/action/entity/time/correlation record |

This is a logical model; introduce it incrementally through migrations rather than creating every table at once.

## 4. Keep relationships distinct
Never compress ownership, possession/control, custodianship, jurisdiction, legal protection, operational responsibility and enforcement authority into one owner_department field. Store relationship type, source and effective dates. Routing selects an operational recipient; it does not determine legal ownership or statutory competence.

## 5. Boundary versioning — mandatory
For every boundary version preserve geometry, CRS, kind, legal status, source document, issuing authority, issue/effective dates, valid-time interval, recorded time, importer/reviewer/approver, supersedes/derived-from links and geometry hash.

A correction inserts a new version; it never overwrites the old geometry. Historical alerts retain the exact boundary version and rule version used. A derived, OSM, model-generated or manually digitised geometry cannot be represented as certified/notified without approval by the competent authority.

Use both valid time (when a fact is in force) and transaction time (when the platform learned/recorded it). A change date is bracketed by last clear and first changed observations, not guessed.

## 6. Evidence and audit
Evidence metadata includes SHA-256 or stronger approved hash, media type, size, capture/acquisition time, source, storage URI, provenance, access class and retention class. Evidence manifests reference original scene IDs, licence, hashes, model/dataset/config versions, candidate geometry, asset/boundary/rule versions, field checks and human decisions.

A hash detects byte changes relative to a recorded hash; it does not prove source authenticity, image interpretation or illegality. Electronic evidence certificates and signatory authority require legal approval. Audit events should be append-only and tamper-evident, with periodic protected checkpoints.

## 7. Multi-department access
Use RBAC plus ABAC. Role controls permitted actions; attributes constrain department, jurisdiction, asset category, sensitivity, case assignment and purpose. Apply API authorisation and database row-level security. UI hiding is not security. Protect owner/claimant names and sensitive court/field information. Preserve the prototype owner-blind principle.

## 8. PostGIS guidance
Use validated geometry with explicit SRID; GiST indexes for spatial columns; B-tree for identifiers/status; metric projected CRS for area/distance; indexed bounding-box filters before exact intersections. Keep raster bytes in object storage/COG, not transactional Postgres. Partition large time-series tables only after workload measurement. Use FKs, unique source IDs, valid-time constraints and database-enforced immutability where required.

## 9. Data quality
Every import has source owner, authority class, schema mapping version, CRS/geometry validation, coverage/completeness, duplicate/conflict report, retrieval time, batch ID and reconciliation status. Conflicts are recorded and routed to source owners; they are not silently resolved.