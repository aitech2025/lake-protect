"""Offline base-map tiles for the fictional demo world (M9: the demo runs with no internet).

Tiles are a drawing of invented places, so they need no login. Tiles outside the demo area are
plain land.
"""
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Response

from app.storage import store

router = APIRouter(prefix="/tiles", tags=["tiles"])
_CACHE = {"Cache-Control": "public, max-age=86400"}


@lru_cache(maxsize=1)
def _blank() -> bytes:
    import io

    from PIL import Image

    from app.seed.demo_render import LAND

    buf = io.BytesIO()
    Image.new("RGB", (256, 256), LAND).save(buf, format="PNG")
    return buf.getvalue()


@router.get("/demo/meta.json")
def meta() -> Response:
    if store.head_object("tiles/demo/meta.json") is None:
        raise HTTPException(404, "Demo tiles have not been rendered. Run python -m app.seed.demo")
    return Response(store.get_object("tiles/demo/meta.json"), media_type="application/json", headers=_CACHE)


@router.get("/demo/{z}/{x}/{y}.png")
def tile(z: int, x: int, y: int) -> Response:
    if not (0 <= z <= 20):
        raise HTTPException(404, "No such tile")
    key = f"tiles/demo/{z}/{x}/{y}.png"
    data = store.get_object(key) if store.head_object(key) is not None else _blank()
    return Response(data, media_type="image/png", headers=_CACHE)
