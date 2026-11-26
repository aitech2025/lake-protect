"""Temporal water-spread comparison for aligned Sentinel-2 MNDWI masks.

Outputs are change-screening geometries, not legal boundary findings. Both masks
must represent comparable seasonal/acquisition conditions and share a valid CRS.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

import numpy as np


def compare_water_masks(reference_path: str | Path, current_path: str | Path,
                        output_dir: str | Path, *, minimum_area_sq_m: float = 400.0, minimum_overlap_ratio: float = 0.5,
                        reference_scene_id: str | None = None, current_scene_id: str | None = None,
                        reference_acquired_at: str | None = None, current_acquired_at: str | None = None,
                        processing_run_id: str | None = None) -> dict[str, Any]:
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.features import shapes
    from rasterio.warp import reproject
    from pyproj import Geod, Transformer
    from shapely.geometry import shape, mapping
    from shapely.ops import transform as transform_geometry
    from .raster import _write_cog

    output_dir=Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    with rasterio.open(reference_path) as ref:
        reference=ref.read(1).astype("float32")
        profile=ref.profile.copy()
        ref_transform,ref_crs=ref.transform,ref.crs
        ref_nodata=ref.nodata
        height,width=ref.height,ref.width
    with rasterio.open(current_path) as cur:
        current=np.empty((height,width),dtype="float32")
        reproject(cur.read(1).astype("float32"),current,
            src_transform=cur.transform,src_crs=cur.crs,
            dst_transform=ref_transform,dst_crs=ref_crs,
            resampling=Resampling.nearest,src_nodata=cur.nodata,dst_nodata=np.nan)
    valid=np.isfinite(reference)&np.isfinite(current)
    if ref_nodata is not None: valid &= reference != ref_nodata
    reference_valid=np.isfinite(reference)
    if ref_nodata is not None: reference_valid &= reference != ref_nodata
    overlap_ratio=float(valid.sum()/max(1,reference_valid.sum()))
    if valid.sum()==0 or overlap_ratio < minimum_overlap_ratio:
        raise ValueError(f"Insufficient scene overlap for temporal comparison: {overlap_ratio:.3f}")
    ref_water=(reference==1)&valid
    cur_water=(current==1)&valid
    loss=np.where(valid,(ref_water&~cur_water).astype("float32"),np.nan)
    gain=np.where(valid,(~ref_water&cur_water).astype("float32"),np.nan)
    loss_path=_write_cog(loss,profile,output_dir/"water-loss.cog.tif")
    gain_path=_write_cog(gain,profile,output_dir/"water-gain.cog.tif")
    transformer=Transformer.from_crs(ref_crs,"EPSG:4326",always_xy=True)
    geod=Geod(ellps="WGS84")
    features=[]
    counts={"water_loss_pixels":int(np.nansum(loss==1)),"water_gain_pixels":int(np.nansum(gain==1))}
    area_totals={"water_loss":0.0,"water_gain":0.0}
    for change_type,array in (("water_loss",loss),("water_gain",gain)):
        mask=np.isfinite(array)&(array==1)
        for geom_json,value in shapes(array.astype("uint8"),mask=mask,transform=ref_transform):
            geom=shape(geom_json)
            geom_wgs84=transform_geometry(transformer.transform,geom)
            area=abs(geod.geometry_area_perimeter(geom_wgs84)[0])
            area_totals[change_type]+=area
            if area < minimum_area_sq_m:
                continue
            features.append({"type":"Feature","geometry":mapping(geom_wgs84),
                "properties":{"change_type":change_type,"area_sq_m":round(area,2),
                    "minimum_area_sq_m":minimum_area_sq_m,"evidence_class":"SCREENING",
                    "validated":False,"reference_scene_id":reference_scene_id,
                    "current_scene_id":current_scene_id,"reference_acquired_at":reference_acquired_at,
                    "current_acquired_at":current_acquired_at,"processing_run_id":processing_run_id}})
    geojson={"type":"FeatureCollection","name":"sentinel_water_spread_change","features":features}
    vector_path=output_dir/"water-change.geojson"
    vector_path.write_text(json.dumps(geojson,ensure_ascii=False),encoding="utf-8")
    return {"water_loss_mask":str(loss_path),"water_gain_mask":str(gain_path),
        "vector_path":str(vector_path),"features":len(features),**counts,
        "water_loss_area_sq_m":round(area_totals["water_loss"],2),
        "water_gain_area_sq_m":round(area_totals["water_gain"],2),
        "method":"temporal binary MNDWI mask difference","validated":False,
        "warning":"Use seasonally comparable images and field/reference validation; changes are screening signals only."}
