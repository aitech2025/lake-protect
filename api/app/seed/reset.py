"""Reset the development database to a clean state with real data only (DECISIONS.md D-065).

    LP_ALLOW_RESET=true python -m app.seed.reset

Append-only tables cannot be emptied row by row, by design, so a reset rebuilds the schema:
migrate down to nothing, migrate up, load the real locations and the role accounts. Generated
chips, field photos, packs, bulletins and the email outbox are removed. The Sentinel-2 base map is
kept. Then restore the real incidents with `lp replay reports/screen/<date>` (no internet needed),
or run a new screen.
"""
from __future__ import annotations

import os
import shutil

from alembic import command
from alembic.config import Config

from app.config import settings
from app.db import SessionLocal, engine
from app.seed import accounts, real_assets
from app.storage import store


def main() -> None:
    if os.environ.get("LP_ALLOW_RESET") != "true":
        raise SystemExit("Refusing to reset: set LP_ALLOW_RESET=true. This deletes every record in the database.")

    engine.dispose()
    cfg = Config("alembic.ini")
    cfg.attributes["url"] = settings.database_url
    command.downgrade(cfg, "0001")  # keep PostGIS: the image's other extensions depend on it
    command.upgrade(cfg, "head")
    for folder in ("chips", "field", "packs", "bulletins", "outbox", "tiles/demo"):
        shutil.rmtree(store.local_path(folder), ignore_errors=True)

    with SessionLocal() as db:
        print("real assets:", real_assets.load(db, settings.data_dir / "assets.geojson"))
        print("role accounts:", accounts.load(db))
    print("Next: lp replay reports/screen/<date> restores the real incidents without internet.")


if __name__ == "__main__":
    main()
