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


if __name__ == "__main__":
    app()
