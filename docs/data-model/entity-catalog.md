# Entity Catalogue and Data Dictionary

This catalogue describes the logical entities, their purpose, principal keys and implementation status. For exact physical columns and constraints, use the referenced Alembic migration. **Do not infer that a target entity exists physically merely because it appears in the logical model.**

## 1. Identity, departments and administration

| Entity / table | Key and relationships | Purpose | Status |
|---|---|---|---|
| `users` | bigint `id`; referenced by access, alerts and field work | Application identities, role, language and active status | Implemented / legacy |
| `departments` | UUID `id`; self-parent | Department and agency directory; parent-child hierarchy | Implemented |
| `administrative_units` | UUID `id`; self-parent | State, district, mandal, ULB, village and ward hierarchy with valid dates | Implemented |
| `user_department_access` | UUID `id`; user + department | Effective-dated READ, CONTRIBUTE or MANAGE grant | Implemented |
| `asset_admin_links` | asset UUID + administrative-unit UUID + valid_from | Effective-dated asset-to-administration link; supports multiple administrative relationships | Implemented |

**Rules:** department hierarchy is not the same as administrative geography. A department's parent is an organizational relationship; a district/mandal/village is a geographic administrative relationship.

## 2. Canonical asset and cadastral model

| Entity / table | Key and relationships | Purpose | Status |
|---|---|---|---|
| `public_assets` | UUID `id`; optional unique `legacy_asset_id` → `assets.id` | Canonical statewide public-asset identity, category, lifecycle, centroid/footprint and source authority | Implemented |
| `land_parcels` | UUID `id`; survey number + subdivision + administrative codes | Cadastral parcel identity and optional footprint/classification | Implemented |
| `asset_parcels` | composite asset UUID + parcel UUID + valid_from | Many-to-many relationship, overlap area, relation type and validity | Implemented |
| `asset_responsibilities` | UUID `id`; asset UUID + department UUID | Effective-dated OWNER, CUSTODIAN, POSSESSOR, JURISDICTION, OPERATIONAL, ENFORCEMENT and DATA_STEWARD relationships | Implemented |
| `asset_categories` | Target key: category code | Governed category definitions, metadata schema, validation and category-specific rule-pack reference | Target |
| `asset_identifiers` | Target UUID; asset UUID | Multiple external IDs per asset (department code, GIS ID, survey reference, source-system key), namespace and validity | Target |
| `asset_metadata_values` | Target UUID; asset UUID/category schema | Typed category-specific attributes with schema version and provenance | Target |

**Important distinctions:**
- A lake, forest block or government-land holding is a platform asset; a survey-number parcel is a cadastral unit. Do not use a survey number as the asset's primary key.
- A parcel may overlap multiple assets, and a single asset may cover multiple parcels.
- Do not store only one `owner_department` on an asset. Responsibility is a relationship with type, source and valid dates.
- Current `public_assets.category_code` is a flexible text code. A governed category registry and category-specific metadata schemas are target enhancements, not present tables.

## 3. Boundary, source and data-ingestion lineage

| Entity / table | Key and relationships | Purpose | Status |
|---|---|---|---|
| `boundaries` | bigint `id`; legacy `asset_id`; self-links for supersedes/derivation | Immutable lake-domain boundary versions: geometry, kind/status, source, validity and hash | Implemented / legacy |
| `asset_boundaries` | Target UUID; canonical asset UUID; boundary source | Canonical cross-domain immutable boundary versions, independent of lake bigint IDs | Target |
| `boundary_sources` | Target UUID; boundary version + source record | Notifications, survey records, government orders, certification and issuing authority | Target |
| `ingestion_batches` | UUID `id` | Source-system import batch, schema/mapping versions, counts, checksum and result | Implemented |
| `source_records` | UUID `id`; optional batch UUID | Individual source records, authority class, source version, effective time, retrieval time, checksum and validation state | Implemented |
| `data_quality_issues` | Target UUID; source record/batch/entity | Duplicate, missing, invalid geometry, conflicting authority and reconciliation exceptions | Target |
| `data_reconciliation_decisions` | Target UUID; issue + reviewer | Human decision and rationale for conflicting source records; retains superseded values | Target |

**Authority classes:** AUTHORITATIVE, CERTIFIED, DERIVED, EXTERNAL, FIELD, MODEL and UNVERIFIED. An OpenStreetMap feature, model output or manually digitised polygon is not an official boundary merely because it is geometrically plausible.

**Boundary version requirements:** preserve geometry, SRID, kind, legal status, source document, issuing authority, issue/effective dates, recorded time, importer/reviewer/approver, supersedes/derived-from links and geometry hash. A correction creates a new version; never overwrite historical legal geometry.

## 4. Earth observation and intelligence

| Entity / table | Key and relationships | Purpose | Status |
|---|---|---|---|
| `satellite_scenes` | UUID `id`; unique provider + collection + item | STAC scene metadata, acquisition time, footprint, licence, cloud cover, object URI and checksum | Implemented schema foundation |
| `observations` | bigint `id`; scene/sensor/acquisition metadata | Observation records used by current lake candidate workflow | Implemented / legacy |
| `processing_runs` | UUID `id`; correlation UUID | Pipeline/version/config hash, input/output manifests, geographic scope, status and retry information | Implemented schema foundation |
| `processing_run_scenes` | Target composite run + scene key | Explicit many-to-many scene/run lineage and processing role | Target |
| `raster_products` | Target UUID; run + source scene | COGs, masks, indices, chips and derived products with URI, CRS, bands, resolution and checksum | Target |
| `candidates` | bigint `id`; legacy asset + boundary IDs | Detected change footprint, class, temporal bracket, sensor basis, confidence and rule version | Implemented / legacy |
| `candidate_asset_links` | UUID `id`; candidate + canonical asset + optional parcel/boundary/run | Reconciliation of a detected change to one or more canonical assets and the exact boundary used | Implemented |
| `candidate_predictions` | UUID `id`; candidate bigint | Versioned score, score type, feature schema, features, factors and disclaimer | Implemented |
| `candidate_observations` | Target composite candidate + observation | Normalized many-to-many link replacing the legacy `observation_ids` array after migration | Target |
| `candidate_reviews` | Target UUID; candidate + reviewer | Human triage decision, reason, review state, timestamps and supersession | Target |

**Detection contract:** a candidate is a claim that an observable change may have occurred in a footprint and time bracket. It is not a legal finding, proof of encroachment, ownership decision or calibrated probability.

The current `candidate_predictions` table supports REVIEW_PRIORITY, DETECTOR_CONFIDENCE and CALIBRATED_PROBABILITY score types. The existence of the latter enum value does not mean a calibrated model is deployed. The current baseline is an explainable review-priority heuristic.

## 5. Legal references and operational response

| Entity / table | Key and relationships | Purpose | Status |
|---|---|---|---|
| `permits` | bigint `id`; spatial footprint and validity | Existing lake-domain permit reference | Implemented / legacy |
| `authorised_works` | bigint `id`; spatial footprint and validity | Existing lake-domain authorized work reference | Implemented / legacy |
| `court_cases` | bigint `id`; optional legacy asset, survey refs and geometry | Existing court-matter reference and legal hold context | Implemented / legacy |
| `legal_references` | Target UUID; canonical asset/parcel + source | Unified permits, leases, grants, notifications, court matters, stays and disputes | Target |
| `candidate_legal_checks` | Target UUID; candidate + boundary + rule pack | Immutable category-specific legal rule evaluation and matched references | Target |
| `legal_checks` | bigint `id`; candidate + exact legacy boundary version | Current lake legal screening result, flags, matched permit/work/court case and rule version | Implemented / legacy |
| `alerts` | bigint `id`; unique candidate | Operational work item, state, priority, owner and due/escalation metadata | Implemented / legacy |
| `cases` | Target UUID; canonical asset + candidate/alert | Cross-domain case identity and formal lifecycle, separate from a detection candidate | Target |
| `case_assignments` | Target UUID; case + department/user | Assignment history, role, dates, reason and reassignment | Target |
| `closure_requests` | bigint `id`; alert + requester/resolver | Two-person/controlled closure request and resolution | Implemented / legacy |
| `field_checks` | bigint `id`; alert + officer; unique client UUID | Offline-safe field verification, geolocation, outcome and photo references | Implemented / legacy |
| `owner_claims` | bigint `id`; alert | Existing lake workflow for claims; sensitive claimant data | Implemented / legacy |
| `readiness_items` | bigint `id`; alert | Checklist for action/evidence readiness | Implemented / legacy |
| `officer_records` | bigint `id`; alert | Officer action and response record | Implemented / legacy |
| `imagery_requests` | bigint `id`; alert | Existing operational imagery request | Implemented / legacy |

Legal screening and formal legal adjudication must remain separate. Rules are category-specific and versioned. A spatial intersection is a reason to review, not a conclusion about title, legality or statutory jurisdiction.

## 6. Evidence, audit, notifications and reporting

| Entity / table | Key and relationships | Purpose | Status |
|---|---|---|---|
| `evidence_packs` | bigint `id`; alert + version | Versioned evidence pack and manifest integrity | Implemented / legacy |
| `evidence_objects` | Target UUID; canonical case/asset + object URI | Individual immutable evidence metadata, media type, size, hash, source, capture time, access and retention class | Target |
| `audit_log` | Existing legacy key; actor/entity/action | Current application audit history and hash-chain support | Implemented / legacy |
| `audit_checkpoints` | Target UUID; audit sequence/range | Periodic externally protected checkpoint/hash anchoring | Target |
| `outbox_events` | bigint `id`; unique event UUID | Transactional event publication, aggregate, correlation, payload and delivery state | Implemented |
| `notifications` | Target UUID; event + recipient | User delivery preferences, channel, attempt, acknowledgement and deduplication | Target |
| `bulletins` | Existing legacy key | Saved monthly operational snapshots | Implemented / legacy |
| `report_snapshots` | Target UUID; scope + period + creator | Versioned report snapshot and reproducible query/filter metadata | Target |

Object bytes belong in object storage; relational rows retain metadata and verified object references. Audit hash chaining is tamper-evident relative to stored hashes, but it is not an independently immutable archive until protected checkpoints are anchored outside the primary database.

## 7. Platform reference tables and event semantics

### Category-specific configuration (target)

- `asset_categories`: stable category code, label, description, owning policy domain, active dates.
- `asset_category_schemas`: JSON Schema or equivalent typed attribute contract, schema version and effective dates.
- `rule_packs`: category, rule name/version, effective dates, approval status and executable/configuration reference.
- `legal_reference_types`: governed reference taxonomy and required metadata.
- `source_systems`: source owner, authority class, access/licence terms, refresh policy and integration contract.

### Event envelope

The existing `outbox_events` table is the transactional event source. New event contracts should include:
- `event_id` (globally unique, idempotency key)
- `event_type` and `schema_version`
- `aggregate_type` and `aggregate_id`
- `correlation_id` and optional causation ID
- `occurred_at`
- `payload` with identifiers and minimal data (avoid sensitive evidence bytes)
- publication/attempt metadata maintained by the dispatcher

Delivery is at-least-once. Every consumer must be idempotent.

## 8. Physical schema references

| Migration | Model scope |
|---|---|
| `0002_data_model.py` | Legacy lake operational tables and core spatial workflow |
| `0004_statewide_platform_foundation.py` | Departments, administrative units, canonical assets, parcels, responsibilities, source ingestion, satellite scenes, processing runs, candidate links, ML registry and outbox |
| `0005_department_security_and_predictions.py` | Department access, candidate predictions, ingestion idempotency and RLS |
| `0007_legacy_domain_rls.py` | Department-scoped RLS for legacy lake domain |
| `0008_boundary_manage_policy.py`–`0010_scoped_bulletins.py` | Boundary management, auditor visibility and report/bulletin scoping |

The current SQLAlchemy legacy mappings are in `api/app/models.py`; statewide mappings are in `api/app/platform/models.py`. Alembic migrations remain authoritative for actual DDL.
