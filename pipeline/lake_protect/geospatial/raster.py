"""Sentinel spectral screening and COG output; baselines are not validated models."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import numpy as np

def _href(item: dict[str, Any], *names: str) -> str:
    for name in names:
        if name in item.get("assets", {}):
            asset=item["assets"][name]
            return asset.get("href") if isinstance(asset,dict) else str(asset)
    raise ValueError("STAC item missing required band: " + ", ".join(names))

def _write_cog(array: np.ndarray, profile: dict[str, Any], output: str | Path) -> Path:
    import rasterio
    output=Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    profile={**profile,"driver":"GTiff","count":1,"dtype":"float32","nodata":-9999.0,"compress":"deflate","tiled":True}
    temp=output.with_suffix(".tmp.tif")
    with rasterio.open(temp,"w",**profile) as dst: dst.write(np.where(np.isfinite(array),array,-9999).astype("float32"),1)
    with rasterio.open(temp) as src: rasterio.shutil.copy(src,output,driver="COG",compress="DEFLATE",overview_resampling="NEAREST")
    temp.unlink(missing_ok=True)
    with rasterio.open(output) as check:
        if check.tags(ns="IMAGE_STRUCTURE").get("LAYOUT") != "COG":
            output.unlink(missing_ok=True); raise RuntimeError("GDAL did not produce a Cloud Optimized GeoTIFF")
    return output

def sentinel2_mndwi(item: dict[str, Any], output: str | Path, *, threshold: float = 0.0) -> dict[str, Any]:
    import rasterio
    from rasterio.warp import reproject, Resampling
    green_href=_href(item,"B03","green"); swir_href=_href(item,"B11","swir16")
    with rasterio.open(green_href) as src:
        green=src.read(1).astype("float32"); profile=src.profile.copy(); nodata=src.nodata
        transform,crs=src.transform,src.crs; height,width=src.height,src.width
    swir=np.empty((height,width),dtype="float32")
    with rasterio.open(swir_href) as src:
        reproject(src.read(1).astype("float32"),swir,src_transform=src.transform,src_crs=src.crs,
            dst_transform=transform,dst_crs=crs,resampling=Resampling.bilinear,
            src_nodata=src.nodata,dst_nodata=np.nan)
    valid=np.isfinite(green)&np.isfinite(swir)
    if nodata is not None: valid &= green != nodata
    denom=green+swir; valid &= np.abs(denom)>1e-6
    index=np.full(green.shape,np.nan,dtype="float32"); index[valid]=(green[valid]-swir[valid])/denom[valid]
    mask=np.where(valid,(index>threshold).astype("float32"),np.nan)
    output=Path(output); index_path=_write_cog(index,profile,output.with_name(output.stem+"_mndwi.tif"))
    mask_path=_write_cog(mask,profile,output)
    pixels=int(np.nansum(mask==1)); pixel_area=abs(profile["transform"].a*profile["transform"].e)
    return {"index_path":str(index_path),"mask_path":str(mask_path),"threshold":threshold,
        "valid_pixels":int(valid.sum()),"water_pixels":pixels,"water_area_sq_m":pixels*pixel_area,
        "method":"Sentinel-2 MNDWI threshold baseline","validated":False}

def sentinel1_vv_screen(item: dict[str, Any], output: str | Path, *, threshold_db: float = -17.0) -> dict[str, Any]:
    import rasterio
    href=_href(item,"vv","VV","measurement")
    with rasterio.open(href) as src:
        vv=src.read(1).astype("float32"); profile=src.profile.copy()
        units=(src.tags().get("units") or src.tags().get("UNITTYPE") or "").lower()
        if units not in {"db","decibel","decibels"}:
            raise ValueError("Sentinel-1 input must be calibrated terrain-corrected backscatter in dB")
        mask=np.where(np.isfinite(vv),(vv<threshold_db).astype("float32"),np.nan)
    path=_write_cog(mask,profile,output); pixels=int(np.nansum(mask==1))
    area=abs(profile["transform"].a*profile["transform"].e)
    return {"mask_path":str(path),"threshold_db":threshold_db,"water_pixels":pixels,
        "water_area_sq_m":pixels*area,"method":"Sentinel-1 VV threshold screen","validated":False}
