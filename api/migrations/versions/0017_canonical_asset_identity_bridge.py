"""Propagate canonical GeoGuard UUID identity into the legacy operational domain.

Revision ID: 0017
Revises: 0016

The bigint operational IDs remain stable for backward compatibility. The UUID registry identity
is authoritative for cross-domain joins. Reported-place support rows are deliberately excluded.
"""
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    -- Ensure the explicit one-to-one bridge exists even on databases upgraded from older pilots.
    ALTER TABLE public_assets ADD COLUMN IF NOT EXISTS legacy_asset_id bigint;
    CREATE UNIQUE INDEX IF NOT EXISTS ux_public_assets_legacy_asset_id
      ON public_assets(legacy_asset_id) WHERE legacy_asset_id IS NOT NULL;

    ALTER TABLE assets ADD COLUMN IF NOT EXISTS platform_asset_id uuid;
    CREATE UNIQUE INDEX IF NOT EXISTS ux_assets_platform_asset_id
      ON assets(platform_asset_id) WHERE platform_asset_id IS NOT NULL;

    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='fk_assets_platform_asset') THEN
        ALTER TABLE assets ADD CONSTRAINT fk_assets_platform_asset
          FOREIGN KEY (platform_asset_id) REFERENCES public_assets(id) ON DELETE RESTRICT;
      END IF;
    END $$;

    -- A reported_place row is only an internal adapter for the legacy incident engine. It is not
    -- a registered asset and must never be attached to the authoritative registry.
    UPDATE public_assets SET legacy_asset_id = NULL
      WHERE category_code = 'reported_place' AND legacy_asset_id IS NOT NULL;
    UPDATE assets SET platform_asset_id = NULL WHERE type::text = 'reported_place';

    -- Backfill a permanent, non-geographic code for every existing operational asset.
    INSERT INTO public_assets
      (asset_code, display_name, category_code, legacy_asset_id, baseline_date,
       source_authority, source_record_ref)
    SELECT 'TG-LEGACY-' || lpad(a.id::text, 8, '0'),
           a.name, a.type::text, a.id, a.baseline_date,
           'DERIVED', 'legacy:assets:' || a.id::text
    FROM assets a
    WHERE a.type::text <> 'reported_place'
      AND NOT EXISTS (
        SELECT 1 FROM public_assets p
        WHERE p.legacy_asset_id = a.id OR p.asset_code = 'TG-LEGACY-' || lpad(a.id::text, 8, '0')
      );

    UPDATE assets a
       SET platform_asset_id = p.id
      FROM public_assets p
     WHERE p.legacy_asset_id = a.id
       AND a.type::text <> 'reported_place'
       AND a.platform_asset_id IS DISTINCT FROM p.id;

    -- Never silently leave an operational asset without its canonical identity.
    DO $$
    BEGIN
      IF EXISTS (
        SELECT 1 FROM assets a
        WHERE a.type::text <> 'reported_place' AND a.platform_asset_id IS NULL
      ) THEN
        RAISE EXCEPTION 'Canonical GeoGuard identity backfill incomplete for one or more operational assets';
      END IF;
    END $$;

    ALTER TABLE assets ADD CONSTRAINT ck_assets_have_platform_identity
      CHECK (type::text = 'reported_place' OR platform_asset_id IS NOT NULL) NOT VALID;
    ALTER TABLE assets VALIDATE CONSTRAINT ck_assets_have_platform_identity;

    -- Propagate the UUID to operational records while retaining bigint FKs and API compatibility.
    ALTER TABLE boundaries ADD COLUMN IF NOT EXISTS platform_asset_id uuid;
    ALTER TABLE candidates ADD COLUMN IF NOT EXISTS platform_asset_id uuid;
    ALTER TABLE alerts ADD COLUMN IF NOT EXISTS platform_asset_id uuid;
    ALTER TABLE monitoring_changes ADD COLUMN IF NOT EXISTS platform_asset_id uuid;
    ALTER TABLE signals ADD COLUMN IF NOT EXISTS platform_asset_id uuid;

    UPDATE boundaries b SET platform_asset_id = a.platform_asset_id
      FROM assets a WHERE a.id=b.asset_id AND b.platform_asset_id IS DISTINCT FROM a.platform_asset_id;
    UPDATE candidates c SET platform_asset_id = a.platform_asset_id
      FROM assets a WHERE a.id=c.asset_id AND c.platform_asset_id IS DISTINCT FROM a.platform_asset_id;
    UPDATE alerts al SET platform_asset_id = c.platform_asset_id
      FROM candidates c WHERE c.id=al.candidate_id AND al.platform_asset_id IS DISTINCT FROM c.platform_asset_id;
    UPDATE monitoring_changes m SET platform_asset_id = a.platform_asset_id
      FROM assets a WHERE a.id=m.asset_id AND m.platform_asset_id IS DISTINCT FROM a.platform_asset_id;
    UPDATE signals s SET platform_asset_id = a.platform_asset_id
      FROM assets a WHERE a.id=s.asset_id AND s.platform_asset_id IS DISTINCT FROM a.platform_asset_id;

    CREATE INDEX IF NOT EXISTS ix_boundaries_platform_asset ON boundaries(platform_asset_id);
    CREATE INDEX IF NOT EXISTS ix_candidates_platform_asset ON candidates(platform_asset_id);
    CREATE INDEX IF NOT EXISTS ix_alerts_platform_asset ON alerts(platform_asset_id);
    CREATE INDEX IF NOT EXISTS ix_monitoring_changes_platform_asset ON monitoring_changes(platform_asset_id);
    CREATE INDEX IF NOT EXISTS ix_signals_platform_asset ON signals(platform_asset_id);

    DO $$
    DECLARE t text;
    BEGIN
      FOREACH t IN ARRAY ARRAY['boundaries','candidates','alerts','monitoring_changes','signals'] LOOP
        IF NOT EXISTS (
          SELECT 1 FROM pg_constraint
          WHERE conname = 'fk_' || t || '_platform_asset'
        ) THEN
          EXECUTE format(
            'ALTER TABLE %I ADD CONSTRAINT %I FOREIGN KEY (platform_asset_id) REFERENCES public_assets(id) ON DELETE RESTRICT',
            t, 'fk_' || t || '_platform_asset'
          );
        END IF;
      END LOOP;
    END $$;

    CREATE OR REPLACE FUNCTION geoguard_sync_asset_identity()
    RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE canonical_id uuid;
    BEGIN
      IF NEW.type::text = 'reported_place' THEN
        NEW.platform_asset_id := NULL;
        RETURN NEW;
      END IF;

      INSERT INTO public_assets
        (asset_code, display_name, category_code, legacy_asset_id, baseline_date,
         source_authority, source_record_ref)
      VALUES
        ('TG-LEGACY-' || lpad(NEW.id::text, 8, '0'), NEW.name, NEW.type::text, NEW.id,
         NEW.baseline_date, 'DERIVED', 'legacy:assets:' || NEW.id::text)
      ON CONFLICT (legacy_asset_id) DO NOTHING;

      SELECT id INTO canonical_id FROM public_assets WHERE legacy_asset_id = NEW.id;
      IF canonical_id IS NULL THEN
        RAISE EXCEPTION 'Unable to resolve canonical GeoGuard identity for legacy asset %', NEW.id;
      END IF;
      NEW.platform_asset_id := canonical_id;
      RETURN NEW;
    END $$;

    CREATE OR REPLACE FUNCTION geoguard_sync_child_asset_identity()
    RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE canonical_id uuid;
    BEGIN
      IF TG_TABLE_NAME = 'alerts' THEN
        SELECT platform_asset_id INTO canonical_id FROM candidates WHERE id = NEW.candidate_id;
      ELSE
        SELECT platform_asset_id INTO canonical_id FROM assets WHERE id = NEW.asset_id;
      END IF;
      NEW.platform_asset_id := canonical_id;
      RETURN NEW;
    END $$;

    DROP TRIGGER IF EXISTS trg_geoguard_asset_identity ON assets;
    CREATE TRIGGER trg_geoguard_asset_identity
      AFTER INSERT OR UPDATE OF type ON assets
      FOR EACH ROW EXECUTE FUNCTION geoguard_sync_asset_identity();

    DROP TRIGGER IF EXISTS trg_geoguard_boundary_identity ON boundaries;
    CREATE TRIGGER trg_geoguard_boundary_identity
      BEFORE INSERT OR UPDATE OF asset_id ON boundaries
      FOR EACH ROW EXECUTE FUNCTION geoguard_sync_child_asset_identity();

    DROP TRIGGER IF EXISTS trg_geoguard_candidate_identity ON candidates;
    CREATE TRIGGER trg_geoguard_candidate_identity
      BEFORE INSERT OR UPDATE OF asset_id ON candidates
      FOR EACH ROW EXECUTE FUNCTION geoguard_sync_child_asset_identity();

    DROP TRIGGER IF EXISTS trg_geoguard_alert_identity ON alerts;
    CREATE TRIGGER trg_geoguard_alert_identity
      BEFORE INSERT OR UPDATE OF candidate_id ON alerts
      FOR EACH ROW EXECUTE FUNCTION geoguard_sync_child_asset_identity();

    DROP TRIGGER IF EXISTS trg_geoguard_monitoring_identity ON monitoring_changes;
    CREATE TRIGGER trg_geoguard_monitoring_identity
      BEFORE INSERT OR UPDATE OF asset_id ON monitoring_changes
      FOR EACH ROW EXECUTE FUNCTION geoguard_sync_child_asset_identity();

    DROP TRIGGER IF EXISTS trg_geoguard_signal_identity ON signals;
    CREATE TRIGGER trg_geoguard_signal_identity
      BEFORE INSERT OR UPDATE OF asset_id ON signals
      FOR EACH ROW EXECUTE FUNCTION geoguard_sync_child_asset_identity();
    """)


def downgrade():
    op.execute("""
    DROP TRIGGER IF EXISTS trg_geoguard_signal_identity ON signals;
    DROP TRIGGER IF EXISTS trg_geoguard_monitoring_identity ON monitoring_changes;
    DROP TRIGGER IF EXISTS trg_geoguard_alert_identity ON alerts;
    DROP TRIGGER IF EXISTS trg_geoguard_candidate_identity ON candidates;
    DROP TRIGGER IF EXISTS trg_geoguard_boundary_identity ON boundaries;
    DROP TRIGGER IF EXISTS trg_geoguard_asset_identity ON assets;
    DROP FUNCTION IF EXISTS geoguard_sync_child_asset_identity();
    DROP FUNCTION IF EXISTS geoguard_sync_asset_identity();
    ALTER TABLE assets DROP CONSTRAINT IF EXISTS ck_assets_have_platform_identity;
    ALTER TABLE assets DROP CONSTRAINT IF EXISTS fk_assets_platform_asset;
    ALTER TABLE boundaries DROP CONSTRAINT IF EXISTS fk_boundaries_platform_asset;
    ALTER TABLE candidates DROP CONSTRAINT IF EXISTS fk_candidates_platform_asset;
    ALTER TABLE alerts DROP CONSTRAINT IF EXISTS fk_alerts_platform_asset;
    ALTER TABLE monitoring_changes DROP CONSTRAINT IF EXISTS fk_monitoring_changes_platform_asset;
    ALTER TABLE signals DROP CONSTRAINT IF EXISTS fk_signals_platform_asset;
    DROP INDEX IF EXISTS ix_boundaries_platform_asset;
    DROP INDEX IF EXISTS ix_candidates_platform_asset;
    DROP INDEX IF EXISTS ix_alerts_platform_asset;
    DROP INDEX IF EXISTS ix_monitoring_changes_platform_asset;
    DROP INDEX IF EXISTS ix_signals_platform_asset;
    ALTER TABLE boundaries DROP COLUMN IF EXISTS platform_asset_id;
    ALTER TABLE candidates DROP COLUMN IF EXISTS platform_asset_id;
    ALTER TABLE alerts DROP COLUMN IF EXISTS platform_asset_id;
    ALTER TABLE monitoring_changes DROP COLUMN IF EXISTS platform_asset_id;
    ALTER TABLE signals DROP COLUMN IF EXISTS platform_asset_id;
    ALTER TABLE assets DROP COLUMN IF EXISTS platform_asset_id;
    DROP INDEX IF EXISTS ux_assets_platform_asset_id;
    DROP INDEX IF EXISTS ux_public_assets_legacy_asset_id;
    """)
