"""Offline base-map tiles (M9: the demo runs with no internet).

- `demo`: a drawing of the fictional demo world. Tiles outside the demo area are plain land.
- `s2`: a Sentinel-2 true-colour mosaic of the area up to the ORR, made by `lp basemap` from
  real scenes at 10 m and uploaded with POST /pipeline/basemap. Outside it, a plain tile.

Tiles need no login: the demo tiles show invented places, and the Sentinel-2 tiles are 10 m
open data, coarser than anything the Indian Space Policy restricts.
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


@lru_cache(maxsize=1)
def _blank_dark() -> bytes:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (256, 256), (38, 42, 40)).save(buf, format="JPEG", quality=80)
    return buf.getvalue()


@router.get("/s2/meta.json")
def s2_meta() -> Response:
    if store.head_object("tiles/s2/meta.json") is None:
        raise HTTPException(404, "The Sentinel-2 base map has not been built. Run lp basemap")
    return Response(store.get_object("tiles/s2/meta.json"), media_type="application/json", headers=_CACHE)


@router.get("/s2/{z}/{x}/{y}.jpg")
def s2_tile(z: int, x: int, y: int) -> Response:
    if not (0 <= z <= 20):
        raise HTTPException(404, "No such tile")
    key = f"tiles/s2/{z}/{x}/{y}.jpg"
    data = store.get_object(key) if store.head_object(key) is not None else _blank_dark()
    return Response(data, media_type="image/jpeg", headers=_CACHE)
