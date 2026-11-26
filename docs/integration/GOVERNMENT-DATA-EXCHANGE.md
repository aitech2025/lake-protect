# GeoGuard — Government Data Exchange Specification

**Version:** 0.1.0-review | **Date:** 26 November 2026  
**Status:** Proposed interface specification for stakeholder review. No live government connection is authorized by this document.

## 1. Purpose

Define a safe, repeatable method for departments to provide authoritative asset, boundary, cadastral and legal reference data to GeoGuard before live system-to-system integrations are approved.

## 2. Supported exchange formats

| Data class | Preferred format | Also accepted | Notes |
|---|---|---|---|
| Vector assets/boundaries | GeoPackage | GeoJSON, Shapefile, KML/KMZ | GeoPackage preferred for multi-layer and CRS metadata |
| Tabular asset register | CSV or XLSX | JSON | Include stable department record ID and data dictionary |
| Raster imagery/elevation | GeoTIFF/COG | Provider archive product | Include CRS, resolution, nodata and acquisition metadata |
| Legal documents | PDF/PDF-A where available | Scanned PDF, TIFF | Include document metadata and source/verification state |
| Reference catalogue | CSV/JSON | XLSX | Include authority, code lists and effective dates |

## 3. Mandatory metadata

Every submission package must include:
- submitting department and authorized contact/role;
- submission ID and date/time;
- source system/register and source record identifiers;
- data custodian and authority to share;
- dataset title, description, category and coverage;
- coordinate reference system (EPSG code or full WKT);
- geometry type and expected units;
- date of source data, effective date and extraction date;
- field dictionary, code lists and null-value semantics;
- licence, permitted use, confidentiality classification and retention constraints;
- declared row/feature count and checksum/manifest;
- known limitations, positional accuracy and prior transformations.

## 4. Asset/boundary fields

Minimum recommended asset attributes:
- department_asset_ref (stable source-system key);
- asset_name_en and asset_name_te (where available);
- asset_category and subcategory;
- custodian_department and responsible_authority;
- district_code, mandal_code, village_code;
- survey_number and subdivision_number (where applicable);
- extent_value and extent_unit;
- geometry and geometry_type;
- CRS/SRID;
- boundary_kind (e.g. core, FTL, buffer, parcel, public-land extent);
- source_document_ref, notification/GO reference and effective date;
- source_status/authority_state (official, derived, submitted, disputed, unverified);
- positional_accuracy_m and validation_notes.

Never use owner personal names as a required ingestion field for detection. Any sensitive ownership information requires separate legal basis, access policy and purpose limitation.

## 5. Intake and validation process

1. **Pre-submission agreement:** agree scope, fields, source authority, data sharing, security and retention.
2. **Secure transfer:** use approved encrypted channel or authenticated API; do not use personal email or public links for sensitive data.
3. **Manifest check:** verify sender, submission ID, file count, hashes, declared counts and allowed formats.
4. **Malware/file safety:** scan files, validate archive contents, prevent path traversal and reject unsupported embedded content.
5. **Schema validation:** required fields, types, code lists, duplicates and referential integrity.
6. **CRS/geometry validation:** explicit CRS, geometry validity, topology, overlap, self-intersection, area and coordinate-range checks.
7. **Spatial validation:** compare against approved administrative boundaries and survey/cadastral context; report discrepancies, never silently snap authoritative data.
8. **GIS review:** reviewer confirms geometry/source interpretation and records findings.
9. **Legal/administrative review:** competent authority separately verifies legal status, notification, custodian and effective date.
10. **Registration:** after approval, assign immutable GeoGuard UUID and human-readable code; retain source IDs and all original files.
11. **Monitoring activation:** only after approved boundary and monitoring policy are established.

## 6. Validation report

Each run should produce:
- submission and file identifiers;
- schema version and validator version;
- file hashes and counts;
- CRS detected/declared and transformation applied;
- invalid/empty/self-intersecting geometries;
- duplicate and overlap candidates;
- area discrepancy and topology findings;
- administrative/survey reference mismatches;
- warnings, errors and reviewer disposition;
- timestamp, actor and immutable report reference.

A validation pass is not an approval. GIS review is not legal certification.

## 7. Boundary version contract

Each boundary version requires:
- asset UUID and boundary version UUID;
- boundary kind and geometry;
- CRS and positional accuracy;
- source record/document and file hash;
- effective-from/effective-to dates;
- creation and review timestamps;
- GIS reviewer and decision;
- legal/administrative approver and authority reference;
- reason for change and superseded version ID;
- status (submitted, derived, GIS-reviewed, legally approved, disputed, superseded).

Never overwrite a boundary in place. A new geometry is a new version. Preserve prior geometry and allow queries as-of a date.

## 8. Future API/connector contract

No live government connector is activated by this specification. When authorized, every connector must define:
- approved endpoint and data owner;
- authentication method and secret rotation;
- data contract and schema version;
- pagination, incremental cursor and change detection;
- idempotency key and replay semantics;
- rate limits, retry/backoff and dead-letter handling;
- provenance and last-success timestamp;
- audit event and error classification;
- data sharing, permitted use, retention and deletion obligations;
- test/sandbox environment and operational owner.

## 9. Security and operational controls

- Encrypt data in transit and at rest.
- Authenticate submitting system and individual where required.
- Use least privilege and scoped service identities.
- Maintain immutable submission and access audit.
- Scan attachments and quarantine suspicious files.
- Keep demo/sample datasets physically/logically separate from authoritative submissions.
- Apply retention, legal hold and disposal policies only after approval.
- Provide reconciliation reports for rejected, partial and duplicate records.

## 10. Open items

Department-specific data dictionaries, official code lists, coordinate standards, custodians, sharing agreements, transfer mechanism, retention, legal approval authority and API details remain open and must be agreed before onboarding production records.
