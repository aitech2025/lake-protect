from lake_protect.geospatial.backtest import evaluate

def feature(fid, geom, **properties):
    return {"type":"Feature","id":fid,"geometry":geom,"properties":properties}

POLYGON={"type":"Polygon","coordinates":[[[78,17],[78.001,17],[78.001,17.001],[78,17.001],[78,17]]]}

def test_backtest_matches_only_before_public_action():
    cases=[feature("case-1",POLYGON,case_id="case-1",area_acres=1,event_date="2025-01-01",public_action_date="2025-03-01")]
    detections=[feature("det-1",POLYGON,detected_at="2025-02-01")]
    result=evaluate(cases,detections)
    assert result["true_positive"]==1 and result["recall"]==1.0

def test_backtest_rejects_detection_after_public_action():
    cases=[feature("case-1",POLYGON,case_id="case-1",area_acres=1,event_date="2025-01-01",public_action_date="2025-03-01")]
    detections=[feature("det-1",POLYGON,detected_at="2025-03-02")]
    result=evaluate(cases,detections)
    assert result["true_positive"]==0 and result["false_negative"]==1
