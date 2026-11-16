# Unified Logical Entity Relationship Diagram

This diagram is a domain-level view. It intentionally groups the current legacy lake workflow and the statewide canonical model. Solid relationships represent current physical foreign-key relationships where present; target entities are marked **(target)** and are not claims about current database tables.

## 1. Asset identity, administration and responsibility

```mermaid
erDiagram
    DEPARTMENTS ||--o{ DEPARTMENTS : parent_of
    ADMINISTRATIVE_UNITS ||--o{ ADMINISTRATIVE_UNITS : parent_of
    PUBLIC_ASSETS ||--o{ ASSET_RESPONSIBILITIES : has
    DEPARTMENTS ||--o{ ASSET_RESPONSIBILITIES : assigned_to
    PUBLIC_ASSETS ||--o{ ASSET_PARCELS : intersects
    LAND_PARCELS ||--o{ ASSET_PARCELS : contains_or_intersects
    PUBLIC_ASSETS ||--o{ ASSET_ADMIN_LINKS : located_in
    ADMINISTRATIVE_UNITS ||--o{ ASSET_ADMIN_LINKS : contains
    USERS ||--o{ USER_DEPARTMENT_ACCESS : granted
    DEPARTMENTS ||--o{ USER_DEPARTMENT_ACCESS : grants
    ASSETS ||--o| PUBLIC_ASSETS : legacy_identity_bridge

    DEPARTMENTS {
      uuid id PK
      text code UK
      text name
      uuid parent_id FK
      boolean is_active
    }
    ADMINISTRATIVE_UNITS {
      uuid id PK
      text code
      text name
      text unit_type
      uuid parent_id FK
      date valid_from
      date valid_to
    }
    PUBLIC_ASSETS {
      uuid id PK
      text asset_code UK
      text display_name
      text category_code
      text lifecycle_status
      bigint legacy_asset_id FK
      geometry footprint
      text source_authority
    }
    LAND_PARCELS {
      uuid id PK
      text survey_number
      text subdivision_number
      text land_classification
      geometry footprint
    }
    ASSET_PARCELS {
      uuid asset_id FK
      uuid parcel_id FK
      date valid_from
      date valid_to
      numeric overlap_area_sq_m
    }
    ASSET_RESPONSIBILITIES {
      uuid id PK
      uuid asset_id FK
      uuid department_id FK
      text relationship_type
      date valid_from
      date valid_to
      text source_record_ref
    }
    ASSET_ADMIN_LINKS {
      uuid asset_id FK
      uuid administrative_unit_id FK
      date valid_from
      date valid_to
    }
    USERS {
      bigint id PK
      text username
      text role
      boolean is_active
    }
    USER_DEPARTMENT_ACCESS {
      uuid id PK
      bigint user_id FK
      uuid department_id FK
      text access_level
      date valid_from
      date valid_to
    }
    ASSETS {
      bigint id PK
      text asset_key
      text type
      text name
    }
```

## 2. Source ingestion, earth observation and candidate lineage

```mermaid
erDiagram
    INGESTION_BATCHES ||--o{ SOURCE_RECORDS : contains
    PROCESSING_RUNS ||--o{ CANDIDATE_ASSET_LINKS : produces_match
    PUBLIC_ASSETS ||--o{ CANDIDATE_ASSET_LINKS : matched_asset
    LAND_PARCELS o|--o{ CANDIDATE_ASSET_LINKS : matched_parcel
    CANDIDATES o|--o{ CANDIDATE_ASSET_LINKS : legacy_candidate
    PROCESSING_RUNS }o--o{ SATELLITE_SCENES : consumes_target
    CANDIDATES ||--o{ CANDIDATE_PREDICTIONS : scored
    CANDIDATES }o--o{ OBSERVATIONS : supported_by_legacy_array

    INGESTION_BATCHES {
      uuid id PK
      text source_system
      text schema_version
      text mapping_version
      text status
      char checksum_sha256
    }
    SOURCE_RECORDS {
      uuid id PK
      uuid batch_id FK
      text source_record_id
      text authority_class
      text validation_status
      jsonb payload
    }
    SATELLITE_SCENES {
      uuid id PK
      text provider
      text collection_id
      text item_id
      timestamptz acquired_at
      geometry footprint
      text license
      text object_uri
    }
    PROCESSING_RUNS {
      uuid id PK
      text pipeline_name
      text pipeline_version
      char config_hash
      text status
      jsonb input_manifest
      jsonb output_manifest
    }
    CANDIDATES {
      bigint id PK
      bigint asset_id FK
      bigint boundary_id FK
      geometry geom
      text change_type
      date first_changed_at
      numeric confidence
    }
    CANDIDATE_ASSET_LINKS {
      uuid id PK
      bigint legacy_candidate_id FK
      uuid platform_asset_id FK
      uuid parcel_id FK
      bigint boundary_id FK
      uuid processing_run_id FK
    }
    CANDIDATE_PREDICTIONS {
      uuid id PK
      bigint candidate_id FK
      text score_type
      numeric score
      text model_version
      jsonb features
    }
    OBSERVATIONS {
      bigint id PK
      text sensor
      text scene_id
      timestamptz acquired_at
    }
```

The current legacy `candidates.observation_ids` is an array, not a normalized FK relationship. A normalized candidate-observation bridge is a target migration once dual-read/backfill/compatibility is planned.

## 3. Legal screening, alerts, field response and evidence

```mermaid
erDiagram
    CANDIDATES ||--o{ LEGAL_CHECKS : screened_by
    BOUNDARIES ||--o{ LEGAL_CHECKS : boundary_version_used
    PERMITS o|--o{ LEGAL_CHECKS : matched_permit
    AUTHORISED_WORKS o|--o{ LEGAL_CHECKS : matched_work
    COURT_CASES o|--o{ LEGAL_CHECKS : matched_case
    CANDIDATES ||--o| ALERTS : opens
    ALERTS ||--o{ FIELD_CHECKS : verified_by
    ALERTS ||--o{ CLOSURE_REQUESTS : closure_workflow
    ALERTS ||--o{ EVIDENCE_PACKS : evidence
    USERS ||--o{ FIELD_CHECKS : officer
    USERS ||--o{ CLOSURE_REQUESTS : requests_or_resolves

    LEGAL_CHECKS {
      bigint id PK
      bigint candidate_id FK
      bigint boundary_id FK
      text result
      text rule_version
      bigint matched_permit_id FK
      bigint matched_work_id FK
      bigint matched_court_case_id FK
    }
    ALERTS {
      bigint id PK
      bigint candidate_id FK
      text state
      numeric priority_score
      bigint owner_user_id FK
      timestamptz due_at
    }
    FIELD_CHECKS {
      bigint id PK
      bigint alert_id FK
      bigint officer_id FK
      uuid client_uuid UK
      timestamptz observed_at
      numeric gps_accuracy_m
      text outcome
    }
    CLOSURE_REQUESTS {
      bigint id PK
      bigint alert_id FK
      bigint requested_by FK
      bigint resolved_by FK
      text reason
      timestamptz requested_at
    }
    EVIDENCE_PACKS {
      bigint id PK
      bigint alert_id FK
      integer version
      char manifest_sha256
    }
    BOUNDARIES {
      bigint id PK
      bigint asset_id FK
      integer version
      text kind
      text status
      geometry geom
      bigint supersedes_id FK
    }
    PERMITS {
      bigint id PK
      text source
      text ref
      geometry geom
      date valid_from
      date valid_to
    }
    AUTHORISED_WORKS {
      bigint id PK
      text agency
      text ref
      geometry geom
      date starts_on
      date ends_on
    }
    COURT_CASES {
      bigint id PK
      text court
      text case_no
      text status
      geometry geom
    }
    USERS {
      bigint id PK
      text username
      text role
    }
```

## 4. ML governance, audit and events

```mermaid
erDiagram
    ML_MODEL_VERSIONS ||--o{ ML_EVALUATIONS : evaluated_by
    OUTBOX_EVENTS }o..o{ ALERTS : event_aggregate_reference
    OUTBOX_EVENTS }o..o{ CANDIDATES : event_aggregate_reference
    AUDIT_LOG }o..o{ USERS : actor_reference

    ML_MODEL_VERSIONS {
      uuid id PK
      text model_name
      text model_version
      text task_type
      text feature_schema_version
      text status
      text artifact_uri
    }
    ML_EVALUATIONS {
      uuid id PK
      uuid model_version_id FK
      text evaluation_type
      text dataset_ref
      jsonb metrics
      boolean passed
    }
    OUTBOX_EVENTS {
      bigint id PK
      uuid event_id UK
      text event_type
      text aggregate_type
      text aggregate_id
      uuid correlation_id
      jsonb payload
      timestamptz published_at
    }
    AUDIT_LOG {
      bigint id PK
      bigint actor_id
      text entity
      text entity_id
      text action
      timestamptz created_at
    }
```

## Relationship rules that are not obvious from the ERD

- `public_assets` is the canonical identity; `assets` is the legacy lake identity during migration.
- `asset_responsibilities` is many-to-many and effective-dated. Do not collapse the relationship types into one owner field.
- `asset_parcels` is many-to-many and effective-dated.
- Boundaries are versioned. Historical candidates and legal checks must retain the exact boundary version they used.
- A candidate can have more than one canonical asset/parcel match. The current `alerts.candidate_id` unique constraint means the current lake workflow permits one alert per candidate; statewide case aggregation across candidates is a target design.
- A prediction is not a human decision. Human review and formal legal outcomes require separate records.
- `outbox_events` are delivered at least once; downstream handlers must deduplicate by `event_id`.
