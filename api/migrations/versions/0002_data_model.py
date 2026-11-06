"""Data model from CONTEXT.md section 7, with append-only and owner-claim guards in the database.

Additions to section 7 are recorded in DECISIONS.md (D-010 onwards):
- users.username, users.is_demo; assets.asset_key; observations.is_demo
- boundaries: version is per asset (a "boundary set"); derived_from_id; created_at
- view boundary_versions derives superseded_by_id and effective_valid_to, because an
  append-only table cannot have valid_to filled in later
- candidates.area_growth; legal_checks.boundary_id, boundary_version, flags
- closure_requests holds the first signature of a two-person closure
- field_checks.client_uuid makes offline sync idempotent

Revision ID: 0002
Revises: 0001
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SQL = r"""
CREATE TYPE cohort AS ENUM ('A_RECOVERED','B_FINAL','C_PRELIM','D_UNNOTIFIED','E_AGENCY','F_REVENUE');
CREATE TYPE asset_type AS ENUM ('lake','recovered_parcel','agency_parcel','revenue_parcel');
CREATE TYPE boundary_kind AS ENUM ('ftl','buffer','parcel','watch_ring');
CREATE TYPE boundary_status AS ENUM ('physically_marked','final_notification','preliminary_notification',
    'derived','surveyed_agency','survey_number_only');
CREATE TYPE zone AS ENUM ('inside_ftl','buffer','watch_ring','outside');
CREATE TYPE change_type AS ENUM ('soil_fill','clearing','small_structure','building','water_loss','other');
CREATE TYPE stage AS ENUM ('soil_dumped','land_levelled','sheds_fences','building_rises','occupied');
CREATE TYPE sensor_basis AS ENUM ('optical_and_radar','optical_only','radar_only');
CREATE TYPE alert_class AS ENUM ('GOVT_LAND','RESTRICTED_PRIVATE','DISPUTED','UNKNOWN');
CREATE TYPE mode AS ENUM ('ACTION','VERIFY','WATCH');
CREATE TYPE alert_state AS ENUM ('CANDIDATE','CLOSED_OUT_OF_SCOPE','CLOSED_LEGACY','CLOSED_AUTHORISED',
    'HOLD_LEGAL','WATCH_LIST','TRIAGE','CLOSED_NOT_REAL','CONFIRMED','ASSIGNED','CLOSED_FALSE_ALARM',
    'FIELD_CONFIRMED','AWAITING_BOUNDARY','PACK_READY','WITH_OFFICER','ACTION_RECORDED',
    'CLOSED_NO_ACTION','POST_ACTION_WATCH');
CREATE TYPE field_outcome AS ENUM ('confirmed','false_alarm','cannot_access');
CREATE TYPE role AS ENUM ('analyst','reviewer','field_officer','nodal_officer','legal_officer',
    'senior_officer','auditor','admin');
CREATE TYPE readiness_status AS ENUM ('yes','no','not_applicable');

CREATE TABLE users (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username text NOT NULL UNIQUE,
    name text NOT NULL,
    role role NOT NULL,
    language text NOT NULL DEFAULT 'en' CHECK (language IN ('en','te')),
    area_geom geometry(MultiPolygon,4326),
    is_active boolean NOT NULL DEFAULT true,
    is_demo boolean NOT NULL DEFAULT false
);

CREATE TABLE assets (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    asset_key text NOT NULL UNIQUE,
    name text NOT NULL,
    name_te text,
    type asset_type NOT NULL,
    cohort cohort NOT NULL,
    district text,
    mandal text,
    village text,
    survey_numbers text[] NOT NULL DEFAULT '{}',
    area_acres numeric(12,3),
    custodian_agency text,
    has_cctv boolean,
    baseline_date date NOT NULL,
    is_demo boolean NOT NULL DEFAULT false,
    notes text
);

CREATE TABLE boundaries (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    asset_id bigint NOT NULL REFERENCES assets(id),
    version integer NOT NULL CHECK (version >= 1),
    kind boundary_kind NOT NULL,
    status boundary_status NOT NULL,
    geom geometry(MultiPolygon,4326) NOT NULL CHECK (ST_IsValid(geom) AND NOT ST_IsEmpty(geom)),
    source_name text NOT NULL,
    source_url text,
    source_date date,
    notification_ref text,
    certified_by text,
    valid_from date NOT NULL,
    valid_to date,
    supersedes_id bigint REFERENCES boundaries(id),
    derived_from_id bigint REFERENCES boundaries(id),
    sha256 char(64) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (asset_id, version, kind),
    CHECK (valid_to IS NULL OR valid_to > valid_from)
);
CREATE INDEX boundaries_geom_gix ON boundaries USING gist (geom);

CREATE TABLE observations (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sensor text NOT NULL,
    scene_id text NOT NULL,
    acquired_at timestamptz NOT NULL,
    cloud_pct numeric(5,2),
    stac_href text,
    processing_version text,
    licence_notice text NOT NULL,
    sha256 char(64),
    is_demo boolean NOT NULL DEFAULT false
);

CREATE TABLE candidates (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    asset_id bigint NOT NULL REFERENCES assets(id),
    boundary_id bigint NOT NULL REFERENCES boundaries(id),
    geom geometry(MultiPolygon,4326) NOT NULL,
    area_sq_m numeric(14,2) NOT NULL CHECK (area_sq_m > 0),
    change_type change_type NOT NULL,
    stage_estimate stage,
    last_clear_at date,
    first_changed_at date NOT NULL,
    observation_ids bigint[] NOT NULL DEFAULT '{}',
    sensor_basis sensor_basis NOT NULL,
    confidence numeric(4,3) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    rule_version text NOT NULL,
    flags text[] NOT NULL DEFAULT '{}',
    before_chip text,
    after_chip text,
    area_growth numeric(8,4),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (last_clear_at IS NULL OR last_clear_at < first_changed_at)
);
CREATE INDEX candidates_geom_gix ON candidates USING gist (geom);

CREATE TABLE permits (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source text NOT NULL,
    ref text NOT NULL,
    geom geometry(MultiPolygon,4326) NOT NULL,
    kind text NOT NULL,
    valid_from date NOT NULL,
    valid_to date,
    is_demo boolean NOT NULL DEFAULT false
);
CREATE INDEX permits_geom_gix ON permits USING gist (geom);

CREATE TABLE authorised_works (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    agency text NOT NULL,
    description text NOT NULL,
    ref text NOT NULL,
    geom geometry(MultiPolygon,4326) NOT NULL,
    starts_on date NOT NULL,
    ends_on date,
    is_demo boolean NOT NULL DEFAULT false
);
CREATE INDEX authorised_works_geom_gix ON authorised_works USING gist (geom);

CREATE TABLE court_cases (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    court text NOT NULL,
    case_no text NOT NULL,
    status text NOT NULL,
    asset_id bigint REFERENCES assets(id),
    survey_numbers text[] NOT NULL DEFAULT '{}',
    geom geometry(MultiPolygon,4326),
    next_hearing date,
    last_checked_at timestamptz,
    is_demo boolean NOT NULL DEFAULT false
);
CREATE INDEX court_cases_geom_gix ON court_cases USING gist (geom);

CREATE TABLE legal_checks (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    candidate_id bigint NOT NULL REFERENCES candidates(id),
    zone zone NOT NULL,
    boundary_status boundary_status NOT NULL,
    mode mode NOT NULL,
    alert_class alert_class NOT NULL,
    result alert_state NOT NULL,
    matched_permit_id bigint REFERENCES permits(id),
    matched_work_id bigint REFERENCES authorised_works(id),
    matched_court_case_id bigint REFERENCES court_cases(id),
    boundary_id bigint NOT NULL REFERENCES boundaries(id),
    boundary_version integer NOT NULL,
    flags text[] NOT NULL DEFAULT '{}',
    rule_version text NOT NULL,
    checked_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE alerts (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code text NOT NULL UNIQUE,
    candidate_id bigint NOT NULL UNIQUE REFERENCES candidates(id),
    state alert_state NOT NULL,
    priority_score numeric(6,2),
    priority_factors jsonb NOT NULL DEFAULT '{}',
    owner_user_id bigint REFERENCES users(id),
    due_at timestamptz,
    escalation_level integer NOT NULL DEFAULT 0 CHECK (escalation_level >= 0),
    reopened_count integer NOT NULL DEFAULT 0 CHECK (reopened_count >= 0),
    is_demo boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE closure_requests (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    alert_id bigint NOT NULL REFERENCES alerts(id),
    from_state alert_state NOT NULL,
    to_state alert_state NOT NULL,
    requested_by bigint NOT NULL REFERENCES users(id),
    reason text NOT NULL,
    reason_code text,
    data jsonb NOT NULL DEFAULT '{}',
    requested_at timestamptz NOT NULL DEFAULT now(),
    resolved_by bigint REFERENCES users(id),
    resolved_at timestamptz,
    resolution text CHECK (resolution IN ('cosigned','withdrawn','superseded')),
    CHECK (resolved_by IS NULL OR resolution <> 'cosigned' OR resolved_by <> requested_by)
);

CREATE TABLE field_checks (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    alert_id bigint NOT NULL REFERENCES alerts(id),
    officer_id bigint NOT NULL REFERENCES users(id),
    client_uuid uuid NOT NULL UNIQUE,
    observed_at timestamptz NOT NULL,
    lat double precision CHECK (lat BETWEEN -90 AND 90),
    lon double precision CHECK (lon BETWEEN -180 AND 180),
    gps_accuracy_m numeric(8,2),
    distance_to_candidate_m numeric(10,2),
    outcome field_outcome NOT NULL,
    observed_stage stage,
    notes text,
    photo_paths text[] NOT NULL DEFAULT '{}',
    photo_sha256 text[] NOT NULL DEFAULT '{}',
    device_time timestamptz,
    synced_at timestamptz NOT NULL DEFAULT now(),
    CHECK (cardinality(photo_paths) = cardinality(photo_sha256))
);

CREATE TABLE owner_claims (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    alert_id bigint NOT NULL REFERENCES alerts(id),
    claim_type text NOT NULL,
    claimant_name text NOT NULL,
    document_ref text,
    entered_by bigint NOT NULL REFERENCES users(id),
    entered_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE readiness_items (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    alert_id bigint NOT NULL REFERENCES alerts(id),
    item_key text NOT NULL,
    status readiness_status NOT NULL,
    evidence_ref text,
    checked_by bigint NOT NULL REFERENCES users(id),
    checked_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (alert_id, item_key)
);

CREATE TABLE evidence_packs (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    alert_id bigint NOT NULL REFERENCES alerts(id),
    version integer NOT NULL CHECK (version >= 1),
    pdf_path text NOT NULL,
    zip_path text NOT NULL,
    manifest_sha256 char(64) NOT NULL,
    generated_by bigint NOT NULL REFERENCES users(id),
    generated_at timestamptz NOT NULL DEFAULT now(),
    counsel_reviewed boolean NOT NULL DEFAULT false,
    UNIQUE (alert_id, version)
);

CREATE TABLE officer_records (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    alert_id bigint NOT NULL REFERENCES alerts(id),
    officer_id bigint NOT NULL REFERENCES users(id),
    notice_ref text,
    notice_date date,
    hearing_date date,
    order_ref text,
    order_date date,
    action_date date,
    action_summary text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE imagery_requests (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    alert_id bigint NOT NULL REFERENCES alerts(id),
    provider text NOT NULL,
    area_sq_km numeric(10,3) NOT NULL,
    est_cost_usd numeric(10,2),
    status text NOT NULL DEFAULT 'recorded',
    requested_by bigint NOT NULL REFERENCES users(id),
    approved_by bigint REFERENCES users(id),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE signals (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kind text NOT NULL,
    asset_id bigint REFERENCES assets(id),
    geom geometry(Geometry,4326),
    received_at timestamptz NOT NULL,
    ref text,
    linked_alert_id bigint REFERENCES alerts(id),
    is_demo boolean NOT NULL DEFAULT false
);

CREATE TABLE audit_log (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_id bigint REFERENCES users(id),
    action text NOT NULL,
    entity text NOT NULL,
    entity_id text,
    details jsonb NOT NULL DEFAULT '{}',
    at timestamptz NOT NULL,
    prev_hash char(64) NOT NULL,
    hash char(64) NOT NULL UNIQUE
);
CREATE INDEX audit_log_entity_idx ON audit_log (entity, entity_id);

CREATE TABLE bulletins (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    month char(7) NOT NULL CHECK (month ~ '^[0-9]{4}-[0-9]{2}$'),
    stats jsonb NOT NULL,
    pdf_path text,
    generated_at timestamptz NOT NULL DEFAULT now()
);

-- Append-only tables: boundaries (invariant 12), audit_log (section 7), evidence_packs (9.3).
CREATE FUNCTION lp_reject_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION '% on % is not allowed: the table is append-only', TG_OP, TG_TABLE_NAME
        USING ERRCODE = 'restrict_violation';
END $$;

CREATE TRIGGER boundaries_append_only BEFORE UPDATE OR DELETE ON boundaries
    FOR EACH ROW EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER boundaries_no_truncate BEFORE TRUNCATE ON boundaries
    FOR EACH STATEMENT EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER audit_log_append_only BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER audit_log_no_truncate BEFORE TRUNCATE ON audit_log
    FOR EACH STATEMENT EXECUTE FUNCTION lp_reject_change();
CREATE TRIGGER evidence_packs_append_only BEFORE UPDATE OR DELETE ON evidence_packs
    FOR EACH ROW EXECUTE FUNCTION lp_reject_change();

-- A new boundary row must belong to the newest version of its asset and supersede the
-- previous row of the same kind. Its hash is computed here from the stored geometry.
CREATE FUNCTION lp_boundary_insert_check() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    max_v integer;
    prev_id bigint;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext('boundaries'), NEW.asset_id::integer);
    SELECT max(version) INTO max_v FROM boundaries WHERE asset_id = NEW.asset_id;
    IF max_v IS NOT NULL AND NEW.version NOT IN (max_v, max_v + 1) THEN
        RAISE EXCEPTION 'boundary version % for asset % must be % or %', NEW.version, NEW.asset_id,
            max_v, max_v + 1 USING ERRCODE = 'check_violation';
    END IF;
    IF max_v IS NULL AND NEW.version <> 1 THEN
        RAISE EXCEPTION 'first boundary version for asset % must be 1', NEW.asset_id
            USING ERRCODE = 'check_violation';
    END IF;
    SELECT id INTO prev_id FROM boundaries
        WHERE asset_id = NEW.asset_id AND kind = NEW.kind AND version < NEW.version
        ORDER BY version DESC LIMIT 1;
    IF NEW.supersedes_id IS DISTINCT FROM prev_id THEN
        RAISE EXCEPTION 'boundary must supersede % (got %)', prev_id, NEW.supersedes_id
            USING ERRCODE = 'check_violation';
    END IF;
    NEW.sha256 := encode(sha256(ST_AsEWKB(NEW.geom)), 'hex');
    RETURN NEW;
END $$;
CREATE TRIGGER boundaries_insert_check BEFORE INSERT ON boundaries
    FOR EACH ROW EXECUTE FUNCTION lp_boundary_insert_check();

-- Superseded rows stay retrievable. Their end date is derived, never written back.
CREATE VIEW boundary_versions AS
SELECT b.*,
       n.id AS superseded_by_id,
       COALESCE(b.valid_to, n.valid_from) AS effective_valid_to
FROM boundaries b
LEFT JOIN LATERAL (
    SELECT x.id, x.valid_from FROM boundaries x WHERE x.supersedes_id = b.id ORDER BY x.version LIMIT 1
) n ON true;

-- Invariant 4, database half: owner claims only once the change is field-confirmed.
CREATE FUNCTION lp_owner_claim_gate() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    s alert_state;
BEGIN
    SELECT state INTO s FROM alerts WHERE id = NEW.alert_id;
    IF s IS NULL OR s NOT IN ('FIELD_CONFIRMED','AWAITING_BOUNDARY','PACK_READY','WITH_OFFICER',
                              'ACTION_RECORDED','CLOSED_NO_ACTION','POST_ACTION_WATCH') THEN
        RAISE EXCEPTION 'owner claims are allowed only after FIELD_CONFIRMED (alert % is %)',
            NEW.alert_id, s USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER owner_claims_gate BEFORE INSERT OR UPDATE ON owner_claims
    FOR EACH ROW EXECUTE FUNCTION lp_owner_claim_gate();
"""


def run_raw(sql: str) -> None:
    """Run multi-statement SQL with no parameters, so '%' in PL/pgSQL RAISE is left alone."""
    with op.get_bind().connection.dbapi_connection.cursor() as cur:
        cur.execute(sql)


def upgrade() -> None:
    run_raw(SQL)


def downgrade() -> None:
    run_raw(
        """
        DROP VIEW IF EXISTS boundary_versions;
        DROP TABLE IF EXISTS bulletins, audit_log, signals, imagery_requests, officer_records,
            evidence_packs, readiness_items, owner_claims, field_checks, closure_requests, alerts,
            legal_checks, court_cases, authorised_works, permits, candidates, observations,
            boundaries, assets, users CASCADE;
        DROP FUNCTION IF EXISTS lp_reject_change, lp_boundary_insert_check, lp_owner_claim_gate;
        DROP TYPE IF EXISTS cohort, asset_type, boundary_kind, boundary_status, zone, change_type,
            stage, sensor_basis, alert_class, mode, alert_state, field_outcome, role, readiness_status;
        """
    )
