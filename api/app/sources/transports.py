"""How a source's files arrive.

- `file_drop`: an officer, or an SFTP job agreed with the department, puts the files and a
  `manifest.yml` in `<LP_STORAGE_DIR>/source-drops/<connector>/`. Works today.
- `sample`: the same, from the fictional files in `app/sources/samples/<connector>/`. Everything
  loaded this way is demo data.
- `api`: a template for the official data-exchange API that a data-sharing agreement would name.
  It refuses to run without an agreement reference, an endpoint and a credential, and it refuses
  HTML: GeoGuard reads files and APIs that a department gives it, never portal pages.
"""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

import httpx
import yaml

from app.sources.base import AgreementRequired, Connector, NotConfigured, Payload, SourceError

SAMPLES_DIR = Path(__file__).parent / "samples"

CONTENT_TYPES = {"csv": "text/csv", "geojson": "application/geo+json"}
_ACCEPTED_TYPES = ("text/csv", "application/geo+json", "application/json")


def _manifest(folder: Path) -> dict:
    path = folder / "manifest.yml"
    if not path.is_file():
        raise SourceError(
            f"{folder.name}: no manifest.yml. Add one with source_date (YYYY-MM-DD) and reference "
            "(the covering letter or agreement number)."
        )
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not data.get("source_date"):
        raise SourceError(f"{folder.name}/manifest.yml: source_date is required")
    return data


class FileDropTransport:
    kind = "file_drop"

    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def waiting(self, connector: Connector) -> list[str]:
        if not self.folder.is_dir():
            return []
        return [d.file_name for d in connector.datasets if (self.folder / d.file_name).is_file()]

    def fetch(self, connector: Connector) -> dict[str, Payload]:
        if not self.folder.is_dir() or not self.waiting(connector):
            raise SourceError(f"{connector.name}: no files in {self.folder}. Drop the files named in the data contract there.")
        manifest = _manifest(self.folder)
        source_date = dt.date.fromisoformat(str(manifest["source_date"]))
        payloads = {}
        for spec in connector.datasets:
            path = self.folder / spec.file_name
            if path.is_file():
                payloads[spec.dataset] = Payload(
                    dataset=spec.dataset,
                    file_name=spec.file_name,
                    content=path.read_bytes(),
                    content_type=CONTENT_TYPES[spec.format],
                    source_date=source_date,
                    reference=manifest.get("reference"),
                    agreement_ref=manifest.get("agreement_ref"),
                )
        connector.check_present(payloads)
        return payloads


class SampleTransport(FileDropTransport):
    kind = "sample"

    def __init__(self, connector_name: str):
        super().__init__(SAMPLES_DIR / connector_name)


class OfficialApiTransport:
    """Template for the API a data-sharing agreement would name. Not callable until then."""

    kind = "api"

    def __init__(self, *, base_url: str | None, agreement_ref: str | None, token_env: str | None,
                 paths: dict[str, str], client: httpx.Client | None = None):
        self.base_url = base_url
        self.agreement_ref = agreement_ref
        self.token_env = token_env
        self.paths = paths
        self.client = client

    @property
    def configured(self) -> bool:
        return bool(self.agreement_ref and self.base_url and self.token_env and os.environ.get(self.token_env))

    def _check(self, connector: Connector) -> str:
        if not self.agreement_ref:
            raise AgreementRequired(
                f"{connector.name}: no data-sharing agreement is recorded with {connector.agency}. "
                "Use the file drop until one is signed, then set agreement_ref in sources.yaml."
            )
        if not self.base_url:
            raise NotConfigured(f"{connector.name}: the agreement names no endpoint yet (api.base_url)")
        token = os.environ.get(self.token_env or "")
        if not token:
            raise NotConfigured(f"{connector.name}: set the credential in {self.token_env}")
        return token

    def fetch(self, connector: Connector) -> dict[str, Payload]:
        token = self._check(connector)
        client = self.client or httpx.Client(timeout=120)
        payloads = {}
        try:
            for spec in connector.datasets:
                path = self.paths.get(spec.dataset)
                if not path:
                    continue
                resp = client.get(
                    self.base_url.rstrip("/") + path,
                    headers={"Authorization": f"Bearer {token}", "Accept": ", ".join(_ACCEPTED_TYPES)},
                )
                if resp.status_code == 404 and not spec.required:
                    continue
                if resp.status_code != 200:
                    raise SourceError(f"{connector.name}: {spec.dataset} returned HTTP {resp.status_code}")
                ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
                if ctype == "text/html":
                    raise SourceError(
                        f"{connector.name}: {spec.dataset} returned a web page. GeoGuard does not read "
                        "portal pages; it needs the data file the agreement describes."
                    )
                if ctype not in _ACCEPTED_TYPES:
                    raise SourceError(f"{connector.name}: {spec.dataset} returned {ctype or 'no content type'}")
                header_date = resp.headers.get("x-source-date")
                payloads[spec.dataset] = Payload(
                    dataset=spec.dataset,
                    file_name=spec.file_name,
                    content=resp.content,
                    content_type=CONTENT_TYPES[spec.format],
                    source_date=dt.date.fromisoformat(header_date) if header_date else dt.date.today(),
                    reference=resp.headers.get("x-source-reference"),
                    agreement_ref=self.agreement_ref,
                )
        finally:
            if self.client is None:
                client.close()
        connector.check_present(payloads)
        return payloads
