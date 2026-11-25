"""End-to-end Sentinel-2 water-screening run with API provenance and S3 COG storage.

Requires LP_API_BASE_URL, LP_PIPELINE_TOKEN, LP_GEO_S3_BUCKET and credentials
supported by boto3. This runner creates screening artefacts only; it does not
create legal findings or enforcement alerts.
"""
from __future__ import annotations
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx


def _json_hash(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _api_client() -> httpx.Client:
    base=os.environ.get("LP_API_BASE_URL","").rstrip("/")
    token=os.environ.get("LP_PIPELINE_TOKEN","")
    if not base or not token:
        raise RuntimeError("LP_API_BASE_URL and LP_PIPELINE_TOKEN are required")
    return httpx.Client(base_url=base, headers={"X-Pipeline-Token":token}, timeout=httpx.Timeout(60, connect=10))


def _s3_client():
    import boto3
    from botocore.config import Config
    bucket=os.environ.get("LP_GEO_S3_BUCKET")
    if not bucket:
        raise RuntimeError("LP_GEO_S3_BUCKET is required; do not leave generated evidence only on worker disk")
    client=boto3.client("s3",endpoint_url=os.getenv("LP_GEO_S3_ENDPOINT_URL") or None,
        region_name=os.getenv("LP_GEO_S3_REGION","ap-south-1") or None,
        aws_access_key_id=os.getenv("LP_GEO_S3_ACCESS_KEY_ID") or None,
        aws_secret_access_key=os.getenv("LP_GEO_S3_SECRET_ACCESS_KEY") or None,
        config=Config(signature_version="s3v4",s3={"addressing_style":"path"},
                      retries={"max_attempts":5,"mode":"standard"}))
    return bucket,client


def _upload(bucket,client,key: str,path: Path,content_type: str = "image/tiff") -> dict:
    data=path.read_bytes()
    digest=hashlib.sha256(data).hexdigest()
    client.put_object(Bucket=bucket,Key=key,Body=data,ContentType=content_type,
                      Metadata={"sha256":digest})
    return {"uri":f"s3://{bucket}/{key}","sha256":digest,"bytes":len(data)}


def run_water_screen(*,endpoint: str,collections: list[str],bbox: list[float],
                     start: str,end: str,max_cloud_pct: float,license_label: str,
                     output_dir: Path) -> dict:
    from pystac_client import Client
    from .catalog import assess_item
    from .raster import sentinel2_mndwi
    if len(bbox)!=4 or bbox[0]>=bbox[2] or bbox[1]>=bbox[3]:
        raise ValueError("bbox must be west,south,east,north EPSG:4326")
    output_dir.mkdir(parents=True,exist_ok=True)
    bucket,s3=_s3_client()
    run_id=str(uuid4())
    scope={"type":"Polygon","coordinates":[[[bbox[0],bbox[1]],[bbox[2],bbox[1]],
        [bbox[2],bbox[3]],[bbox[0],bbox[3]],[bbox[0],bbox[1]]]]}
    config={"collections":collections,"bbox":bbox,"start":start,"end":end,
            "max_cloud_pct":max_cloud_pct,"method":"mndwi-threshold-0.0","version":"0.2.0"}
    manifest={"stac_endpoint":endpoint,"query":config,"created_at":datetime.now(timezone.utc).isoformat()}
    api=_api_client()
    run_payload={"id":run_id,"pipeline_name":"sentinel2-water-screening",
        "pipeline_version":"0.2.0","config_hash":_json_hash(config),
        "input_manifest":manifest,"geographic_scope":scope}
    response=api.post("/api/v1/ingestion/processing-runs",json=run_payload)
    response.raise_for_status()
    api.patch(f"/api/v1/ingestion/processing-runs/{run_id}",
              json={"status":"RUNNING","output_manifest":{}}).raise_for_status()
    items=Client.open(endpoint).search(collections=collections,bbox=bbox,
        datetime=f"{start}/{end}",max_items=200).items()
    outputs=[]; rejected=[]; registered=0; mask_records=[]
    try:
        for item in items:
            decision=assess_item(item,max_cloud_pct=max_cloud_pct)
            item_dict=item.to_dict()
            if not decision.suitable:
                rejected.append({"item_id":item.id,"reasons":list(decision.reasons)})
                continue
            if not item.geometry or item.geometry.get("type")!="Polygon":
                rejected.append({"item_id":item.id,"reasons":["unsupported_or_missing_polygon_footprint"]})
                continue
            item_bytes=json.dumps(item_dict,sort_keys=True,separators=(",",":")).encode()
            item_key=f"lake-protect/stac/{item.id}.json"
            item_digest=hashlib.sha256(item_bytes).hexdigest()
            s3.put_object(Bucket=bucket,Key=item_key,Body=item_bytes,ContentType="application/geo+json",
                          Metadata={"sha256":item_digest})
            acquired=item.properties.get("datetime") or item.properties.get("start_datetime")
            if not acquired:
                rejected.append({"item_id":item.id,"reasons":["missing_acquisition_datetime"]})
                continue
            scene_payload={"provider":"earth-search","collection_id":item.collection_id or collections[0],
                "item_id":item.id,"platform":item.properties.get("platform"),
                "instrument":item.properties.get("instruments",[None])[0] if item.properties.get("instruments") else None,
                "acquired_at":acquired,"footprint":item.geometry,
                "cloud_cover":item.properties.get("eo:cloud_cover"),"gsd_m":item.properties.get("gsd"),
                "license":license_label,"suitability_status":"SUITABLE","stac_item":item_dict,
                "object_uri":f"s3://{bucket}/{item_key}","checksum_sha256":item_digest}
            scene_resp=api.post("/api/v1/ingestion/scenes",json=scene_payload)
            scene_resp.raise_for_status()
            registered+=1
            safe_id=hashlib.sha256(item.id.encode()).hexdigest()[:16]
            mask_local=output_dir/f"{safe_id}-water-mask.cog.tif"
            result=sentinel2_mndwi(item_dict,mask_local,threshold=0.0)
            index_local=Path(result["index_path"])
            mask_obj=_upload(bucket,s3,f"lake-protect/derived/{run_id}/{safe_id}-water-mask.cog.tif",mask_local)
            index_obj=_upload(bucket,s3,f"lake-protect/derived/{run_id}/{safe_id}-mndwi.cog.tif",index_local)
            mask_records.append({"scene_id":item.id,"acquired_at":acquired,"mask_path":mask_local,"geometry":item.geometry})
            outputs.append({"scene_id":item.id,"acquired_at":acquired,
                "scene_registration":scene_resp.json(),"water_mask":mask_obj,"mndwi":index_obj,
                "water_area_sq_m":result["water_area_sq_m"],"valid_pixels":result["valid_pixels"],
                "method":result["method"],"validated":False})
        temporal_change=None
        if len(mask_records) >= 2:
            from datetime import datetime
            from shapely.geometry import shape
            from .change import compare_water_masks
            comparable=[]
            for i in range(len(mask_records)):
                for j in range(i+1,len(mask_records)):
                    a,b=mask_records[i],mask_records[j]
                    da=datetime.fromisoformat(str(a["acquired_at"]).replace("Z","+00:00"))
                    db=datetime.fromisoformat(str(b["acquired_at"]).replace("Z","+00:00"))
                    if da==db:
                        continue
                    earlier,later=(a,b) if da<db else (b,a)
                    ga,gb=shape(earlier["geometry"]),shape(later["geometry"])
                    denominator=min(ga.area,gb.area)
                    overlap=ga.intersection(gb).area/denominator if denominator else 0.0
                    if overlap >= 0.5:
                        gap=(datetime.fromisoformat(str(later["acquired_at"]).replace("Z","+00:00"))-
                             datetime.fromisoformat(str(earlier["acquired_at"]).replace("Z","+00:00"))).total_seconds()
                        comparable.append((gap,overlap,earlier,later))
            if comparable:
                _,footprint_overlap,reference,current=max(comparable,key=lambda row:(row[0],row[1]))
                comparison=compare_water_masks(reference["mask_path"],current["mask_path"],
                    output_dir/f"{run_id}-change",minimum_overlap_ratio=0.5)
                loss_obj=_upload(bucket,s3,f"lake-protect/derived/{run_id}/water-loss.cog.tif",Path(comparison["water_loss_mask"]))
                gain_obj=_upload(bucket,s3,f"lake-protect/derived/{run_id}/water-gain.cog.tif",Path(comparison["water_gain_mask"]))
                vector_obj=_upload(bucket,s3,f"lake-protect/derived/{run_id}/water-change.geojson",
                    Path(comparison["vector_path"]),"application/geo+json")
                temporal_change={"status":"SCREENING_COMPLETE","reference_scene":reference["scene_id"],
                    "current_scene":current["scene_id"],"reference_acquired_at":reference["acquired_at"],
                    "current_acquired_at":current["acquired_at"],"footprint_overlap_ratio":round(footprint_overlap,4),
                    "valid_pixel_overlap_ratio":comparison["overlap_ratio"],
                    "water_loss_mask":loss_obj,"water_gain_mask":gain_obj,"change_features":vector_obj,
                    "water_loss_area_sq_m":comparison["water_loss_area_sq_m"],
                    "water_gain_area_sq_m":comparison["water_gain_area_sq_m"],
                    "feature_count":comparison["features"],"validated":False,"method":comparison["method"]}
            else:
                temporal_change={"status":"NOT_COMPARABLE",
                    "reason":"No pair of observations had at least 50% footprint overlap and distinct acquisition dates."}
        elif len(mask_records)==1:
            temporal_change={"status":"INSUFFICIENT_OBSERVATIONS","reason":"Only one suitable observation was processed."}
        final_status="SUCCEEDED" if outputs and not rejected else ("PARTIAL" if outputs else "FAILED")
        output_manifest={"scene_count":registered,"processed_count":len(outputs),
            "rejected_count":len(rejected),"outputs":outputs,"rejected":rejected,"temporal_change":temporal_change,
            "caveat":"MNDWI threshold screening only; not a legally verified FTL or encroachment determination."}
        api.patch(f"/api/v1/ingestion/processing-runs/{run_id}",
            json={"status":final_status,"output_manifest":output_manifest,
                  "error_code":None if outputs else "NO_SUITABLE_SCENES",
                  "error_detail":None if outputs else "No suitable Sentinel-2 scenes produced outputs."}).raise_for_status()
        return {"run_id":run_id,"status":final_status,**output_manifest}
    except Exception as exc:
        try:
            api.patch(f"/api/v1/ingestion/processing-runs/{run_id}",
                json={"status":"FAILED","output_manifest":{"partial_outputs":outputs},
                      "error_code":"WATER_SCREEN_FAILED","error_detail":type(exc).__name__}).raise_for_status()
        except Exception:
            pass
        raise
    finally:
        api.close()
