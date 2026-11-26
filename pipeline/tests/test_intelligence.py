import pytest
from lake_protect.intelligence.features import CandidateFeatures,FEATURE_NAMES
from lake_protect.intelligence.triage import baseline_triage

def test_owner_blind_versioned_feature_contract():
    f=CandidateFeatures(1200,.25,2,20,.8,1.0,.9)
    assert len(f.to_vector())==len(FEATURE_NAMES)
    assert f.to_dict()["schema_version"]=="1.0"
    assert "owner" not in f.to_dict()

def test_baseline_score_is_explainable_and_not_legal_finding():
    r=baseline_triage(CandidateFeatures(1200,.25,2,20,.8,1.0,.9))
    assert 0<=r.score<=100
    assert r.method=="transparent_baseline_v1"
    assert "not a legal finding" in r.disclaimer
    assert r.factors["boundary_quality"]==1.0

@pytest.mark.parametrize("area",[-1,float("nan"),float("inf")])
def test_invalid_features_rejected(area):
    with pytest.raises(ValueError):
        baseline_triage(CandidateFeatures(area,.1,1,10,.5,.5,.5))
