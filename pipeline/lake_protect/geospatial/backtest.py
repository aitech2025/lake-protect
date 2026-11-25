"""Spatial and temporal backtest scoring for independently verified cases."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from shapely.geometry import shape
ACRE_SQ_M=4046.8564224

def load_features(path: str | Path) -> list[dict[str,Any]]:
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("type")!="FeatureCollection": raise ValueError("Input must be a GeoJSON FeatureCollection")
    return data.get("features",[])

def evaluate(cases: list[dict[str,Any]], detections: list[dict[str,Any]], *, minimum_area_acres: float=0.25, match_iou: float=0.10) -> dict[str,Any]:
    eligible=[]
    for feature in cases:
        geom=shape(feature["geometry"]); props=feature.get("properties",{})
        if not props.get("event_date"):
            raise ValueError("Every ground-truth case must provide event_date for temporal backtesting")
        if props.get("area_acres") is None:
            raise ValueError(f"Case {props.get('case_id', feature.get('id'))} must provide area_acres; degree-based area estimates are not accepted")
        area=float(props["area_acres"])
        if area>=minimum_area_acres: eligible.append((feature,geom))
    remaining=set(range(len(detections))); matches=[]
    for case,case_geom in eligible:
        props=case.get("properties",{}); action=props.get("public_action_date"); event=props.get("event_date"); choices=[]
        for idx in remaining:
            det=detections[idx]; dp=det.get("properties",{}); detected=dp.get("detected_at") or dp.get("first_changed_at")
            if not detected or (action and detected[:10]>=action[:10]) or (event and detected[:10]<event[:10]): continue
            geom=shape(det["geometry"]); union=case_geom.union(geom).area
            iou=case_geom.intersection(geom).area/union if union else 0.0
            if iou>=match_iou: choices.append((iou,idx,detected))
        if choices:
            iou,idx,detected=max(choices); remaining.remove(idx)
            matches.append({"case_id":props.get("case_id",case.get("id")),"detection_id":detections[idx].get("id"),
                "iou":round(iou,4),"detected_at":detected,"before_public_action":True})
    tp=len(matches); fn=len(eligible)-tp; fp=len(remaining)
    precision=tp/(tp+fp) if tp+fp else 0.0; recall=tp/(tp+fn) if tp+fn else 0.0
    f1=2*precision*recall/(precision+recall) if precision+recall else 0.0
    return {"eligible_cases":len(eligible),"excluded_below_minimum_area":len(cases)-len(eligible),
        "detections":len(detections),"true_positive":tp,"false_positive":fp,"false_negative":fn,
        "precision":round(precision,4),"recall":round(recall,4),"f1":round(f1,4),
        "minimum_area_acres":minimum_area_acres,"match_iou":match_iou,"matches":matches,
        "warning":"Screening metrics only; verify labels, dates, CRS and blind-test independence before reporting."}

def evaluate_files(cases_path: str|Path,detections_path: str|Path,output_path: str|Path,*,minimum_area_acres:float=0.25,match_iou:float=0.10):
    result=evaluate(load_features(cases_path),load_features(detections_path),minimum_area_acres=minimum_area_acres,match_iou=match_iou)
    Path(output_path).parent.mkdir(parents=True,exist_ok=True); Path(output_path).write_text(json.dumps(result,indent=2),encoding="utf-8")
    return result
