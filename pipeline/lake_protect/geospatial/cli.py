"""CLI for STAC discovery, spectral screening and backtest evaluation."""
from pathlib import Path
import json
import typer
app=typer.Typer(help="Lake Protect geospatial intelligence commands",no_args_is_help=True)


@app.command("run-water")
def run_water(endpoint:str=typer.Option("https://earth-search.aws.element84.com/v1"),
              collections:str=typer.Option("sentinel-2-c1-l2a"),
              bbox:str=typer.Option(...,help="west,south,east,north EPSG:4326"),
              start:str=typer.Option(...),end:str=typer.Option(...),
              max_cloud_pct:float=typer.Option(35.0,min=0,max=100),
              license_label:str=typer.Option(...,help="Approved licence label for this provider/product"),
              output_dir:Path=typer.Option(Path("data/imagery/work"))):
    from .runner import run_water_screen
    bounds=[float(x.strip()) for x in bbox.split(",")]
    result=run_water_screen(endpoint=endpoint,collections=[x.strip() for x in collections.split(",")],
        bbox=bounds,start=start,end=end,max_cloud_pct=max_cloud_pct,license_label=license_label,output_dir=output_dir)
    typer.echo(json.dumps({k:v for k,v in result.items() if k!="outputs"},indent=2))
    typer.echo("processing_run="+result["run_id"]+" status="+result["status"]+" processed="+str(result["processed_count"]))

@app.command("search")
def search(endpoint:str=typer.Option("https://earth-search.aws.element84.com/v1"),collections:str=typer.Option("sentinel-2-c1-l2a"),
           bbox:str=typer.Option(...,help="west,south,east,north EPSG:4326"),start:str=typer.Option(...),end:str=typer.Option(...),
           max_cloud_pct:float=typer.Option(35.0,min=0,max=100),limit:int=typer.Option(100,min=1,max=1000),
           out:Path=typer.Option(Path("data/imagery/scenes.json"))):
    from .catalog import search_scenes
    bounds=[float(x.strip()) for x in bbox.split(",")]
    rows=search_scenes(endpoint=endpoint,collections=[x.strip() for x in collections.split(",")],bbox=bounds,start=start,end=end,max_cloud_pct=max_cloud_pct,limit=limit)
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(rows,indent=2),encoding="utf-8")
    typer.echo(f"scenes={len(rows)} suitable={sum(bool(x['suitable']) for x in rows)} output={out}")

@app.command("mndwi")
def mndwi(item_json:Path=typer.Argument(...),output:Path=typer.Option(Path("data/imagery/water-mask.cog.tif")),threshold:float=typer.Option(0.0)):
    from .raster import sentinel2_mndwi
    typer.echo(json.dumps(sentinel2_mndwi(json.loads(item_json.read_text(encoding="utf-8")),output,threshold=threshold),indent=2))

@app.command("sar-water")
def sar_water(item_json:Path=typer.Argument(...),output:Path=typer.Option(Path("data/imagery/sar-water-mask.cog.tif")),threshold_db:float=typer.Option(-17.0)):
    from .raster import sentinel1_vv_screen
    typer.echo(json.dumps(sentinel1_vv_screen(json.loads(item_json.read_text(encoding="utf-8")),output,threshold_db=threshold_db),indent=2))

@app.command("validate-cases")
def validate_cases(manifest:Path=typer.Argument(...,exists=True,dir_okay=False,readable=True),
                   output:Path=typer.Option(Path("reports/m3/case-validation.json"))):
    """Validate M3 ground-truth case evidence before scoring."""
    from .cases import validate_case_collection
    collection=json.loads(manifest.read_text(encoding="utf-8"))
    result=validate_case_collection(collection)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2),encoding="utf-8")
    typer.echo(json.dumps(result,indent=2))
    typer.echo(f"report={output}")
    if not result["valid"]:
        raise typer.Exit(code=1)

@app.command("backtest")
def backtest(cases:Path=typer.Argument(...),detections:Path=typer.Argument(...),output:Path=typer.Option(Path("reports/backtest.json")),
             minimum_area_acres:float=typer.Option(0.25,min=0),match_iou:float=typer.Option(0.10,min=0,max=1)):
    from .backtest import evaluate_files
    result=evaluate_files(cases,detections,output,minimum_area_acres=minimum_area_acres,match_iou=match_iou)
    typer.echo(json.dumps({k:v for k,v in result.items() if k!="matches"},indent=2)); typer.echo(f"report={output}")

@app.command("compare-tuning")
def compare_tuning(before:Path=typer.Argument(...,exists=True,dir_okay=False,readable=True),
                   after:Path=typer.Argument(...,exists=True,dir_okay=False,readable=True),
                   output:Path=typer.Option(Path("reports/m2-tuning/run-diff.json")),
                   iou_threshold:float=typer.Option(0.10,min=0,max=1)):
    """Compare two non-scored tuning exports and list footprints needing human review."""
    from .tuning_diff import compare_files
    result=compare_files(before,after,output,iou_threshold=iou_threshold)
    typer.echo(json.dumps({k:v for k,v in result.items() if k not in ("matches","disappeared_candidates","added_candidates")},indent=2))
    typer.echo(f"report={output}")

if __name__=="__main__": app()
