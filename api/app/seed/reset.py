"""Reset the development database to a clean demo state.

    LP_ALLOW_RESET=true python -m app.seed.reset

Append-only tables cannot be emptied row by row, by design, so a reset rebuilds the schema:
migrate down to nothing, migrate up, load the real assets, then seed the fictional demo. Generated
chips and field photos are removed. Base-map tiles are kept unless --tiles is passed.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil

from alembic import command
from alembic.config import Config

from app.config import settings
from app.db import SessionLocal, engine
from app.seed import demo, real_assets
from app.storage import store


def main() -> None:
    if os.environ.get("LP_ALLOW_RESET") != "true":
        raise SystemExit("Refusing to reset: set LP_ALLOW_RESET=true. This deletes every record in the database.")
    parser = argparse.ArgumentParser()
    parser.add_argument("--tiles", action="store_true", help="Re-render base-map tiles too")
    args = parser.parse_args()

    engine.dispose()
    cfg = Config("alembic.ini")
    cfg.attributes["url"] = settings.database_url
    command.downgrade(cfg, "0001")  # keep PostGIS: the image's other extensions depend on it
    command.upgrade(cfg, "head")
    for folder in ("chips", "field", "packs", "bulletins"):
        shutil.rmtree(store.local_path(folder), ignore_errors=True)

    with SessionLocal() as db:
        print("real assets:", real_assets.load(db, settings.data_dir / "assets.geojson"))
        print("demo:", json.dumps(demo.seed(db), indent=1))
    print("tiles rendered:", demo.render_tiles(force=args.tiles))


if __name__ == "__main__":
    main()
