# GeoGuard Government Data Onboarding Specification

**Document ID:** GG-DATA-001  
**Version:** 1.0  
**Status:** Proposed submission contract  
**Applies to:** Participating Telangana government departments and authorised data providers

## 1. Purpose

This specification defines how departments should prepare and submit asset inventory, cadastral/spatial boundaries, legal references and supporting files to GeoGuard. The objective is to minimise rework, preserve source provenance and ensure that no asset is activated for monitoring until the required spatial and legal review is complete.

This is a proposed common exchange contract. Each department's authoritative codes, record definitions, coordinate reference systems and legal requirements must be confirmed with that department before production onboarding.

## 2. Submission package structure

A submission should be delivered as one versioned package using the agreed secure transfer method.

    submission-package/
      manifest.json
      assets.csv
      spatial/
        assets.gpkg
      documents/
        document-index.csv
        <department-document-files>
      raster/
        <optional-georeferenced-maps>
      metadata/
        data-dictionary.xlsx
        code-lists.csv

GeoPackage is the preferred vector exchange format. Alternative formats are accepted only when the required sidecar files, CRS and metadata are included.

## 3. Package-level manifest

The manifest must identify the source department, dataset, submission version, CRS, contacts and included files. A JSON example:

    {
      "schema_version": "1.0",
      "submission_reference": "DEPT-2026-00045",
      "department_code": "DEPT_CODE",
      "department_name": "Submitting Department",
      "source_authority": "Named source authority",
      "dataset_name": "Government asset inventory",
      "dataset_version": "2026-Q4",
      "submitted_at": "2026-11-26T10:00:00+05:30",
      "default_crs": "EPSG:XXXX",
      "contact": {
        "role": "Department GIS Data Owner",
        "official_email": "official departmental address"
      },
      "files": [
        {
          "path": "assets.csv",
          "media_type": "text/csv",
          "sha256": "SHA256_HEX"
        },
        {
          "path": "spatial/assets.gpkg",
          "media_type": "application/geopackage+sqlite3",
          "sha256": "SHA256_HEX"
        }
      ]
    }

The sample values are illustrative. Production code lists, department identifiers and CRS values must be supplied by the government data governance group.

## 4. Asset attribute schema

The following common fields are required unless explicitly marked conditional.

| Field | Type | Required | Rules |
|---|---|---|---|
| source_asset_ref | String | Yes | Stable source-system identifier; do not reuse |
| asset_name | String | Yes | Official name; preserve source spelling |
| asset_name_local | String | No | Local-language name |
| asset_category | Code | Yes | Must use approved category code |
| department_code | Code | Yes | Must match approved department master |
| district_code | Code | Yes | Must match official district master |
| mandal_code | Code | Yes | Must match official mandal master |
| village_code | Code | Conditional | Required where village-level source exists |
| survey_number | String | Conditional | Preserve punctuation, subdivision and leading zeros |
| subdivision_number | String | No | Preserve as source value |
| extent_value | Decimal | Conditional | Numeric extent from source record |
| extent_unit | Code | Conditional | Approved unit: acre, hectare, sqm, etc. |
| legal_status | Code | Yes | Source-declared status; never inferred by GeoGuard |
| source_authority | String | Yes | Authority responsible for the source record |
| source_record_ref | String | Yes | File, register, GO, notification or system reference |
| source_record_date | Date | No | Date on source record |
| effective_from | Date | Conditional | Effective date where applicable |
| effective_to | Date | No | End date where applicable |
| source_crs | String | Yes for spatial data | EPSG code or complete WKT |
| geometry_ref | String | Yes for spatial asset | Feature ID/key in spatial file |
| data_owner_role | String | Yes | Departmental accountable role |
| notes | String | No | Additional source notes |

Do not use a free-text legal status as a substitute for legal documents. Controlled values should be agreed with the authority, for example: notified, recorded, under-verification, disputed, superseded or not-applicable. These are illustrative values only.

## 5. Spatial data requirements

### 5.1 Geometry

- Submit the source-authoritative geometry, not a hand-drawn approximation unless explicitly identified as indicative.
- Include a stable feature key that joins the geometry to source_asset_ref.
- Declare geometry type: Point, LineString, Polygon, MultiPolygon or MultiLineString as appropriate.
- Polygon rings must be closed and geometries must be valid.
- Do not dissolve multiple survey parcels into one feature if survey-level traceability is required.
- If multiple geometry components represent one asset, provide stable part identifiers and explain their relationship.
- Do not embed FTL, buffer and cadastral boundary as an indistinguishable single polygon. Submit them as separate layers with separate source metadata.

### 5.2 Coordinate reference system

- Every spatial file and layer must declare its CRS.
- Prefer the source department's official CRS for cadastral data; do not reproject source files without retaining the original.
- If latitude/longitude is supplied, state the datum and axis order explicitly.
- EPSG:4326 may be used for interchange only when the source coordinates genuinely use WGS 84.
- GeoGuard may create a derived display/analysis copy in an approved CRS; the source geometry remains preserved.
- Transformation method, source CRS, target CRS and processing software/version must be recorded.
- Area and distance calculations must use a suitable projected CRS and must not be represented as survey-grade measurements unless the underlying source and method support that claim.

### 5.3 Suggested GeoPackage layers

| Layer | Geometry | Purpose |
|---|---|---|
| asset_footprint | Polygon/MultiPolygon | Main asset boundary |
| cadastral_parcels | Polygon/MultiPolygon | Survey parcel geometry |
| ftl_boundary | Polygon/MultiPolygon | Officially sourced FTL boundary, where applicable |
| buffer_zone | Polygon/MultiPolygon | Officially sourced buffer geometry, where applicable |
| feeder_channels | LineString/MultiLineString | Nala, feeder and channel references |
| access_points | Point | Optional entrances or field reference points |
| reference_locations | Point | Optional named landmarks |

Each layer must include source authority, source reference, source date, CRS and verification state in its metadata or linked submission record.

## 6. Lake-specific extension

For lake and water-body assets, submit where available:

- Official asset/lake identifier and name.
- Notified extent and unit.
- FTL geometry and the legal/technical source defining it.
- Buffer geometry and the applicable order/rule/source.
- Survey numbers and subdivisions intersecting the lake or associated land.
- Feeder, nala, surplus course and channel relationships.
- GO/notification number, issuing authority, issue date and effective date.
- Source department and legal verification status.

FTL, buffer and visible water spread are different concepts. Current satellite water extent must never replace the legally notified FTL boundary.

## 7. Legal document index

Provide one row per document.

| Field | Required | Description |
|---|---|---|
| source_document_ref | Yes | Stable reference from submitting department |
| file_path_or_uri | Yes | Path in package or approved repository reference |
| document_type | Yes | GO, notification, survey record, order, plan, court record, etc. |
| issuing_authority | Yes | Issuing authority |
| document_number | Conditional | Official reference number |
| issue_date | Conditional | Date issued |
| effective_from | Conditional | Effective date |
| effective_to | No | Expiry/end date if applicable |
| related_source_asset_ref | Conditional | Asset to which it applies |
| related_boundary_type | No | Asset, cadastral, FTL, buffer, etc. |
| verification_status | Yes | Submitted, verified, disputed, superseded, etc. |
| access_classification | Yes | Public, official, restricted or other approved class |
| language | No | Document language |
| page_count | No | Number of pages, if known |
| checksum_sha256 | Yes for file | File integrity checksum |

Scanned documents should be legible and complete. OCR output is an index aid and must not be treated as the authoritative legal text. Where page-level citations are required, retain the original page order.

## 8. Raster and imagery submissions

For georeferenced raster maps, provide GeoTIFF or Cloud Optimized GeoTIFF where possible, with:

- CRS and geotransform.
- Pixel size / ground sample distance.
- Acquisition or source date.
- Sensor/provider and product identifier.
- Band descriptions and data type.
- NoData value.
- Processing level and any resampling.
- Licence and permitted use.
- SHA-256 checksum.

A scanned map without georeferencing must be labelled as an unreferenced document. It must not be displayed as if it were accurately aligned to the ground.

## 9. Validation performed by GeoGuard

### 9.1 File and package checks

- Required files exist and match the manifest.
- File types are permitted and files pass malware scanning.
- Checksums match.
- Archives do not contain path traversal or unsafe content.
- File sizes and row/feature counts are within configured limits.

### 9.2 Attribute checks

- Required columns and types are present.
- Codes exist in approved master lists.
- Duplicate source_asset_ref values are detected.
- Dates and units are valid.
- Survey identifiers are retained as strings.
- Extent values are positive and unit is explicit.

### 9.3 Geometry checks

- CRS is explicit and supported.
- Geometry is parseable, non-empty and valid.
- Geometry type matches the asset category.
- Coordinate values are plausible for the declared CRS and jurisdiction.
- Self-intersections, invalid rings, duplicate geometries and suspicious overlaps are flagged.
- Geometry-derived extent is compared with declared extent as a QA warning, not silently substituted.
- Spatial joins to district/mandal/village boundaries are checked and mismatches are reported.

### 9.4 Legal and provenance checks

- Document references resolve to an included file or approved external source.
- Issuing authority and dates are present where required.
- Boundary source and verification state are explicit.
- A legal reviewer can distinguish submitted, reviewed and approved material.
- The platform does not infer legal status from geometry or imagery.

## 10. Validation report and feedback contract

GeoGuard returns a submission-level report containing:

- Submission ID and receipt timestamp.
- Package validation status.
- File-level and record-level results.
- Error code, severity, field/layer/feature reference and remediation guidance.
- Counts of accepted, rejected and pending-review records.
- GIS review and legal review status.
- Resubmission/version reference.
- Asset IDs created only after formal approval.

Suggested validation severities:

- BLOCKER: submission cannot proceed to review.
- ERROR: affected record cannot be registered until corrected.
- WARNING: record may proceed only if reviewer accepts the documented limitation.
- INFO: informational observation.

## 11. Registration and change control

- Receipt of a dataset does not create an approved Asset ID.
- Candidate records remain in staging until validation and required reviews are complete.
- Approved registration creates a permanent platform Asset ID and an initial boundary version.
- Later source corrections create a new submission and proposed version.
- A reviewer must compare the proposed version with the active version.
- An authorised approver records the decision, effective date and supporting source.
- Previous versions remain queryable and linked to detections/cases that used them.
- Asset merge, split, transfer and retirement are explicit lifecycle operations with lineage.
- Hard deletion and identifier reuse are prohibited for registered assets.

## 12. Secure submission and operational controls

- Use government-approved SFTP, API gateway or secure upload portal.
- Do not send sensitive cadastral/legal files through personal email or consumer file-sharing links.
- Authenticate submitting departments and record the submitting user/service.
- Encrypt transfer and storage.
- Restrict package access to assigned reviewers.
- Log download, validation, review, approval and export events.
- Define retention and archival with the source authority.
- Maintain separate test and production submissions.
- Use synthetic or explicitly approved masked data for demonstrations.

## 13. Department onboarding checklist

- [ ] Department and source authority are identified.
- [ ] Department data owner and technical contact are nominated.
- [ ] Asset categories and official identifiers are agreed.
- [ ] Administrative master codes are agreed.
- [ ] Source CRS and coordinate conventions are documented.
- [ ] Geometry layers and attribute dictionary are supplied.
- [ ] Legal document index is complete.
- [ ] Sample package passes validation.
- [ ] Data-sharing and permitted-use terms are approved.
- [ ] Reviewers and approvers are configured.
- [ ] Resubmission and correction process is agreed.
- [ ] Production transfer method and access controls are approved.

## 14. Decisions to finalise with each authority

1. Authoritative source system and accountable data owner.
2. Asset category-specific mandatory fields.
3. Official district, mandal, village and department codes.
4. Required CRS and cadastral exchange conventions.
5. Rules for survey number, subdivision and extent representation.
6. Legal documents required to approve each asset category.
7. Whether geometries are authoritative, indicative or derived.
8. Update frequency and change-notification process.
9. Data classification, permitted use, retention and onward sharing.
10. Approval authority for registration, boundary version and retirement.

## 15. Example CSV header

    source_asset_ref,asset_name,asset_category,department_code,district_code,mandal_code,village_code,survey_number,subdivision_number,extent_value,extent_unit,legal_status,source_authority,source_record_ref,source_record_date,effective_from,source_crs,geometry_ref,data_owner_role

The header is a common baseline. Department-specific fields must be added through a versioned schema rather than silently changing the meaning of existing fields.
