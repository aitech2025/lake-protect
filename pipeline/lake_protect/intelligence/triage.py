"""Safe inference facade: transparent fallback only, not a trained model."""
from dataclasses import dataclass
from .features import CandidateFeatures, FEATURE_SCHEMA_VERSION

@dataclass(frozen=True)
class TriageResult:
    score: float
    method: str
    model_version: str
    feature_schema_version: str
    factors: dict[str,float]
    disclaimer: str = "Screening priority only; not a legal finding."

def baseline_triage(features: CandidateFeatures) -> TriageResult:
    features.validate()
    factors={
      "area":min(1.0,(features.area_sq_m/10000.0)**0.5),
      "growth":min(1.0,max(0.0,features.area_growth)),
      "persistence":min(1.0,features.persistence_count/3.0),
      "temporal_quality":1.0 if features.observation_gap_days<=45 else max(0.0,1.0-(features.observation_gap_days-45.0)/180.0),
      "sensor_agreement":features.sensor_agreement,
      "boundary_quality":features.boundary_quality,
      "stage_preventability":features.stage_preventability,
    }
    weights={"area":.12,"growth":.18,"persistence":.20,"temporal_quality":.10,
             "sensor_agreement":.12,"boundary_quality":.13,"stage_preventability":.15}
    score=round(100*sum(factors[k]*weights[k] for k in weights),2)
    return TriageResult(score,"transparent_baseline_v1","baseline-1.0.0",FEATURE_SCHEMA_VERSION,factors)
