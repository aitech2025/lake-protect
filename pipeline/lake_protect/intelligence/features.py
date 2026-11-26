"""Versioned, owner-blind feature contract. Claimant identity is intentionally excluded."""
from dataclasses import asdict, dataclass
from math import isfinite

FEATURE_SCHEMA_VERSION = "1.0"
FEATURE_NAMES = ("area_sq_m","area_growth","persistence_count","observation_gap_days",
                 "sensor_agreement","boundary_quality","stage_preventability")

@dataclass(frozen=True)
class CandidateFeatures:
    area_sq_m: float
    area_growth: float
    persistence_count: int
    observation_gap_days: float
    sensor_agreement: float
    boundary_quality: float
    stage_preventability: float

    def validate(self):
        for name,value in asdict(self).items():
            if not isfinite(float(value)):
                raise ValueError(f"{name} must be finite")
        if self.area_sq_m < 0 or self.persistence_count < 0 or self.observation_gap_days < 0:
            raise ValueError("area, persistence and observation gap cannot be negative")
        for name in ("sensor_agreement","boundary_quality","stage_preventability"):
            if not 0 <= getattr(self,name) <= 1:
                raise ValueError(f"{name} must be between 0 and 1")

    def to_vector(self):
        self.validate()
        return [float(getattr(self,name)) for name in FEATURE_NAMES]

    def to_dict(self):
        self.validate()
        return {"schema_version":FEATURE_SCHEMA_VERSION,**asdict(self)}
