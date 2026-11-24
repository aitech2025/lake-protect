"""`lp` command line. Heavy geospatial imports stay inside each command."""
import typer

app = typer.Typer(help="Lake Protect pipeline commands.", no_args_is_help=True)


@app.callback()
def main() -> None:
    """Lake Protect pipeline commands."""


@app.command()
def version() -> None:
    """Print the pipeline version."""
    from lake_protect import __version__

    typer.echo(__version__)


@app.command("verify-pack")
def verify_pack(
    zip_path: str = typer.Argument(..., help="Evidence pack zip."),
    manifest_sha256: str = typer.Option(None, help="Manifest hash recorded for this pack, to catch a rewritten manifest."),
) -> None:
    """Recompute every hash in an evidence pack. Exits 1 if anything changed."""
    from lake_protect.packverify import verify

    result = verify(zip_path, manifest_sha256)
    typer.echo(f"manifest sha256: {result['manifest_sha256']}")
    typer.echo(f"files checked:   {result['files_checked']}")
    for problem in result["problems"]:
        typer.echo(f"FAIL  {problem}")
    typer.echo("PASS  every file matches its hash" if result["ok"] else "FAIL  the pack does not match its manifest")
    raise typer.Exit(0 if result["ok"] else 1)


@app.command("assets-osm")
def assets_osm(
    search: str = typer.Option("data/case_lake_search.yml", help="Name patterns per case lake."),
    out: str = typer.Option("data/assets.geojson", help="Output asset file."),
    raw: str = typer.Option("data/sources/overpass_water_orr.json", help="Saved Overpass response."),
    refetch: bool = typer.Option(False, help="Query Overpass again instead of using the saved response."),
) -> None:
    """Build real assets from OpenStreetMap water polygons (status `derived`, cohort D)."""
    from pathlib import Path

    from lake_protect.osm_assets import build

    result = build(Path(search), Path(raw), Path(out), refetch)
    typer.echo(f"Overpass elements: {result['elements']}, matched features: {result['features']}")
    for case, hits in result["matches"].items():
        label = "no OSM match" if not hits else ("unique" if len(hits) == 1 else f"AMBIGUOUS x{len(hits)}")
        typer.echo(f"  {case:<24} {label:<14} " + "; ".join(f"{h['name']} [{h['osm']}, {h['area_acres']} ac]" for h in hits))


def _date(value: str | None):
    import datetime as dt

    return dt.date.fromisoformat(value) if value else None


def _print_results(results, meta) -> None:
    from lake_protect.screen import asset_summary

    typer.echo(f"\n{meta['rule_version']}  as of {meta['as_of']}  ({meta['seconds']} s)")
    for r in results:
        s = asset_summary(r)
        typer.echo(
            f"  {s['name'][:34]:<34} {s['status']:<16} looks {s['looks']:>3} "
            f"({s['first_look'] or '-'} to {s['last_look'] or '-'})  candidates {s['candidates']}  before-baseline {s['legacy_changes']}"
        )
        for c in r.candidates:
            typer.echo(
                f"      {c['change_type']:<10} {c['area_sq_m']:>7.0f} sq m  last clear {c['last_clear_at']}  first changed {c['first_changed_at']}"
                f"  looks {c['looks_changed']}  conf {c['confidence']}  {','.join(c['flags'])}"
            )


@app.command()
def detect(
    asset: list[str] = typer.Option(None, "--asset", help="asset_key from the asset file. Repeat for several. Default: all."),
    assets: str = typer.Option("data/assets.geojson", help="Asset file."),
    as_of: str = typer.Option(None, help="Use only scenes acquired on or before this date (default: today)."),
    baseline: str = typer.Option(None, help="Override every asset's baseline date."),
    out: str = typer.Option(None, help="Report folder (default reports/detect/<as_of>)."),
    workers: int = typer.Option(16, help="Parallel reads."),
    chips: bool = typer.Option(True, help="Render before and after chips."),
) -> None:
    """Detect change on Sentinel-2 for assets in the asset file and write a report folder."""
    import datetime as dt
    from pathlib import Path

    from lake_protect.screen import aois_from_file, run, write_report

    day = _date(as_of) or dt.date.today()
    aois = aois_from_file(Path(assets), asset or None, _date(baseline))
    results, meta = run(aois, day, workers=workers, with_chips=chips, log=typer.echo)
    folder = write_report(results, meta, Path(out or f"reports/detect/{day.isoformat()}"))
    _print_results(results, meta)
    typer.echo(f"\nReport: {folder}")


@app.command()
def screen(
    api: str = typer.Option("http://localhost:8100", envvar="LP_API_URL", help="Lake Protect API."),
    token: str = typer.Option(..., envvar="LP_PIPELINE_TOKEN", help="Pipeline token (LP_PIPELINE_TOKEN)."),
    as_of: str = typer.Option(None, help="Use only scenes acquired on or before this date (default: today)."),
    asset: list[str] = typer.Option(None, "--asset", help="Limit to these asset_keys."),
    out: str = typer.Option(None, help="Report folder (default reports/screen/<as_of>)."),
    workers: int = typer.Option(16, help="Parallel reads."),
    dry_run: bool = typer.Option(False, help="Detect and write the report, but send nothing to the API."),
    repeat_hours: float = typer.Option(0, help="Run again every this many hours (the scheduled container uses 168, weekly). 0: once."),
) -> None:
    """Weekly screen: watch list from the API, Sentinel-2 detection, candidates and coverage sent back."""
    import time

    while True:
        try:
            _screen_once(api, token, as_of, asset, out, workers, dry_run)
        except Exception as exc:  # a scheduled run that fails is logged and retried next time
            if not repeat_hours:
                raise
            typer.echo(f"Screen failed: {type(exc).__name__}: {exc}")
        if not repeat_hours:
            return
        typer.echo(f"Next screen in {repeat_hours} hours")
        time.sleep(repeat_hours * 3600)


def _screen_once(api, token, as_of, asset, out, workers, dry_run) -> None:
    import datetime as dt
    from pathlib import Path

    import httpx

    from lake_protect.screen import aois_from_watchlist, api_payload, asset_summary, image_payload, run, write_report

    day = _date(as_of) or dt.date.today()
    headers = {"X-Pipeline-Token": token}
    with httpx.Client(base_url=api, headers=headers, timeout=120) as client:
        resp = client.get("/pipeline/watchlist")
        resp.raise_for_status()
        aois = aois_from_watchlist(resp.json()["assets"], asset or None)
        typer.echo(f"Watch list: {len(aois)} assets")
        started = dt.datetime.now(dt.timezone.utc)
        results, meta = run(aois, day, workers=workers, log=typer.echo)
        folder = write_report(results, meta, Path(out or f"reports/screen/{day.isoformat()}"))
        _print_results(results, meta)
        outcomes: dict[str, int] = {}
        sent = []
        changes: dict[str, list[dict]] = {}
        for r in results:
            for c in r.candidates:
                if dry_run:
                    continue
                resp = client.post("/candidates", json=api_payload(c))
                if resp.status_code == 201:
                    body = resp.json()
                    outcomes[body["outcome"]] = outcomes.get(body["outcome"], 0) + 1
                    sent.append({"asset_key": r.aoi.asset_key, **{k: body[k] for k in ("outcome", "alert_code", "state")}})
                    changes.setdefault(r.aoi.asset_key, []).append({k: body[k] for k in ("candidate_id", "alert_id", "outcome")})
                    typer.echo(f"  -> {r.aoi.name}: {body['alert_code']} {body['outcome']} {body['state']}")
                else:
                    outcomes[f"refused_{resp.status_code}"] = outcomes.get(f"refused_{resp.status_code}", 0) + 1
                    typer.echo(f"  -> {r.aoi.name}: refused {resp.status_code} {resp.text[:200]}")
        if not dry_run:
            run_body = {
                **{k: meta[k] for k in ("as_of", "rule_version", "rules_sha256", "collection")},
                "started_at": started.isoformat(),
                "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "outcomes": outcomes,
                "assets": [{k: v for k, v in asset_summary(r).items() if k not in ("asset_key", "name")}
                           | image_payload(r) | {"changes": changes.get(r.aoi.asset_key, [])} for r in results],
            }
            resp = client.post("/pipeline/runs", json=run_body)
            typer.echo(f"Run recorded: {resp.status_code} {resp.text[:200]}")
        typer.echo(f"Outcomes: {outcomes or 'none sent'}\nReport: {folder}")


@app.command()
def replay(
    report: str = typer.Argument(..., help="A report folder written by lp screen (holds summary.json and payloads.jsonl)."),
    api: str = typer.Option("http://localhost:8100", envvar="LP_API_URL"),
    token: str = typer.Option(..., envvar="LP_PIPELINE_TOKEN"),
) -> None:
    """Resend a saved screen to the API: its candidates, then its coverage. Needs no internet.

    Used after a demo reset, which rebuilds the database. Assets are matched by asset_key, so new
    database ids do not matter. Ingest is the normal path: the legal check and the state machine run
    again, and an alert already open on the same change is not duplicated.
    """
    import datetime as dt
    import json
    from pathlib import Path

    import httpx

    folder = Path(report)
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    with httpx.Client(base_url=api, headers={"X-Pipeline-Token": token}, timeout=120) as client:
        ids = {a["asset_key"]: a["id"] for a in client.get("/pipeline/watchlist").raise_for_status().json()["assets"]}
        outcomes: dict[str, int] = {}
        for line in (folder / "payloads.jsonl").read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            if item["asset_key"] not in ids:
                typer.echo(f"  skip {item['asset_key']}: not on the watch list")
                continue
            body = {**item["payload"], "asset_id": ids[item["asset_key"]]}
            resp = client.post("/candidates", json=body)
            key = resp.json().get("outcome", "created") if resp.status_code == 201 else f"refused_{resp.status_code}"
            outcomes[key] = outcomes.get(key, 0) + 1
            if resp.status_code != 201:
                typer.echo(f"  {item['asset_key']}: {resp.status_code} {resp.text[:160]}")
        import base64

        assets = []
        for a in summary["assets"]:
            if a["asset_key"] in ids:
                row = {k: v for k, v in a.items() if k not in ("asset_key", "name", "image_file")} | {"asset_id": ids[a["asset_key"]]}
                image = folder / a["image_file"] if a.get("image_file") else None
                if image is not None and image.is_file():
                    row["image_png_b64"] = base64.b64encode(image.read_bytes()).decode()
                assets.append(row)
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        body = {k: summary[k] for k in ("as_of", "rule_version", "rules_sha256", "collection")}
        body |= {"started_at": summary.get("started_at", now), "finished_at": summary.get("finished_at", now), "outcomes": outcomes, "assets": assets}
        resp = client.post("/pipeline/runs", json=body)
        typer.echo(f"Candidates: {outcomes}. Coverage for {len(assets)} assets: {resp.status_code} {resp.text[:160]}")


@app.command()
def basemap(
    as_of: str = typer.Option(None, help="Use scenes acquired on or before this date (default: today)."),
    days: int = typer.Option(75, help="Look back this many days for clear scenes."),
    out: str = typer.Option(None, help="Zip to write (default <LP_CACHE_DIR>/basemap/s2_<as_of>.zip)."),
    upload: bool = typer.Option(False, help="Send the zip to the API (POST /pipeline/basemap)."),
    api: str = typer.Option("http://localhost:8100", envvar="LP_API_URL"),
    token: str = typer.Option(None, envvar="LP_PIPELINE_TOKEN"),
) -> None:
    """Build the offline Sentinel-2 base map for the area up to the ORR."""
    import datetime as dt
    from pathlib import Path

    from lake_protect.basemap import build
    from lake_protect.rules import cache_dir

    day = _date(as_of) or dt.date.today()
    target = Path(out) if out else cache_dir() / "basemap" / f"s2_{day.isoformat()}.zip"
    build(target, day, days=days, log=typer.echo)
    if upload:
        import httpx

        if not token:
            raise SystemExit("LP_PIPELINE_TOKEN is needed to upload")
        with target.open("rb") as fh:
            resp = httpx.post(f"{api}/pipeline/basemap", headers={"X-Pipeline-Token": token}, files={"file": (target.name, fh, "application/zip")}, timeout=600)
        typer.echo(f"Upload: {resp.status_code} {resp.text[:200]}")


if __name__ == "__main__":
    app()
