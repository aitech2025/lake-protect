"""Shared types for the asset creation engine (docs/asset-engine.md).

A connector knows one government source: which files it publishes (its data contract), how to
read them and how its statuses map onto ours. A transport knows how the files arrive. The
engine (app.sources.engine) does everything else: snapshots, validation, matching,
reconciliation and publishing, the same way for every source.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class SourceError(ValueError):
    """A source cannot be read as it stands. The message says what to fix."""


class NotConfigured(SourceError):
    """The transport is missing a setting (an endpoint or a credential)."""


class AgreementRequired(SourceError):
    """No data-sharing agreement is recorded for this source, so it cannot be called."""


@dataclass(frozen=True)
class DatasetSpec:
    """One file in a source's data contract."""

    dataset: str
    file_name: str
    format: str  # "csv" or "geojson"
    required: bool
    fields: tuple[str, ...]
    description: str
    optional_fields: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "dataset": self.dataset,
            "file_name": self.file_name,
            "format": self.format,
            "required": self.required,
            "fields": list(self.fields),
            "optional_fields": list(self.optional_fields),
            "description": self.description,
        }


@dataclass(frozen=True)
class Payload:
    """One file as received, before anything is read from it."""

    dataset: str
    file_name: str
    content: bytes
    content_type: str
    source_date: dt.date
    reference: str | None = None
    agreement_ref: str | None = None


@dataclass
class BoundaryRecord:
    kind: str  # "ftl" or "parcel"
    status: str  # a BoundaryStatus value
    geometry: dict
    source_name: str
    source_date: dt.date
    source_url: str | None = None
    notification_ref: str | None = None
    certified_by: str | None = None
    positional_accuracy_m: float | None = None
    dataset: str = ""  # the file the outline came from


@dataclass
class AssetRecord:
    """A lake or parcel as one source describes it."""

    external_id: str
    name: str
    asset_type: str  # an AssetType value
    custodian_agency: str
    name_te: str | None = None
    district: str | None = None
    mandal: str | None = None
    village: str | None = None
    survey_numbers: list[str] = field(default_factory=list)
    area_acres: float | None = None
    has_cctv: bool | None = None
    # IDs the same asset has in other sources, e.g. {"hmda_lpc": "S-001"}.
    crosswalk: dict[str, str] = field(default_factory=dict)
    boundary: BoundaryRecord | None = None
    dataset: str = ""


@dataclass
class ParcelRecord:
    """A survey-number parcel. There is no field for an owner's name, by design."""

    district: str
    mandal: str
    village: str
    survey_no: str
    sub_division: str
    land_category: str
    geometry: dict
    recorded_category: str | None = None
    bhudhaar: str | None = None
    extent_acres: float | None = None
    positional_accuracy_m: float | None = None
    dataset: str = ""

    @property
    def label(self) -> str:
        return f"{self.survey_no}/{self.sub_division}" if self.sub_division else self.survey_no


@dataclass
class Parsed:
    assets: list[AssetRecord] = field(default_factory=list)
    parcels: list[ParcelRecord] = field(default_factory=list)
    # Records refused while reading, each {"ref": ..., "reason": ...}.
    rejected: list[dict] = field(default_factory=list)
    # Records read but not loaded yet, each {"ref": ..., "reason": ...}.
    waiting: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)


class Connector(ABC):
    """One government source. Subclasses declare their contract and read their own files."""

    name: str
    agency: str
    licence_note: str
    key_prefix: str
    datasets: tuple[DatasetSpec, ...]
    summary: str

    def spec(self, dataset: str) -> DatasetSpec:
        for d in self.datasets:
            if d.dataset == dataset:
                return d
        raise KeyError(dataset)

    def check_present(self, payloads: dict[str, Payload]) -> None:
        missing = [d.file_name for d in self.datasets if d.required and d.dataset not in payloads]
        if missing:
            raise SourceError(f"{self.name}: missing required file(s): {', '.join(missing)}")
        if not payloads:
            raise SourceError(f"{self.name}: no files to read")

    @abstractmethod
    def parse(self, payloads: dict[str, Payload]) -> Parsed:
        """Read the files into records. Must not touch the database."""

    def describe(self) -> dict:
        return {
            "name": self.name,
            "agency": self.agency,
            "summary": self.summary,
            "licence_note": self.licence_note,
            "datasets": [d.as_dict() for d in self.datasets],
        }


# Reading helpers shared by connectors -------------------------------------------------------


def read_csv(payload: Payload, spec: DatasetSpec) -> list[dict]:
    reader = csv.DictReader(io.StringIO(payload.content.decode("utf-8-sig")))
    columns = [c.strip() for c in (reader.fieldnames or [])]
    missing = [f for f in spec.fields if f not in columns]
    if missing:
        raise SourceError(f"{spec.file_name}: missing column(s): {', '.join(missing)}")
    return [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in reader]


def read_geojson(payload: Payload, spec: DatasetSpec) -> list[dict]:
    try:
        doc = json.loads(payload.content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceError(f"{spec.file_name}: not GeoJSON ({exc})") from exc
    if doc.get("type") != "FeatureCollection":
        raise SourceError(f"{spec.file_name}: expected a FeatureCollection")
    features = doc.get("features") or []
    for n, f in enumerate(features, start=1):
        props = f.get("properties") or {}
        missing = [k for k in spec.fields if k not in props]
        if missing:
            raise SourceError(f"{spec.file_name}: feature {n} is missing {', '.join(missing)}")
    return features


def as_date(value, what: str) -> dt.date:
    try:
        return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value).strip())
    except ValueError as exc:
        raise SourceError(f"{what}: not a date ({value!r}); use YYYY-MM-DD") from exc


def as_float(value) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise SourceError(f"not a number: {value!r}") from exc


def split_list(value: str | None) -> list[str]:
    return [s.strip() for s in (value or "").split(";") if s.strip()]
