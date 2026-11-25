"""Monthly page map (SVG) and the one-page PDF (section 9.4)."""
from __future__ import annotations

import base64
import math
from pathlib import Path
from xml.sax.saxutils import escape

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import text
from sqlalchemy.orm import Session

TEMPLATES = Path(__file__).with_name("templates")
FONTS = Path(__file__).resolve().parents[1] / "assets" / "fonts"
_env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html"]))
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def month_label(month: str) -> str:
    y, m = month.split("-")
    return f"{MONTHS[int(m) - 1]} {y}"


def map_svg(db: Session, stats: dict, *, width: int = 640, height: int = 400) -> str:
    """Every lake and parcel, with this month's new incidents and those waiting for a decision marked."""
    rows = db.execute(text(
        """
        SELECT a.name, a.type::text AS type, ST_AsGeoJSON(ST_SimplifyPreserveTopology(b.geom, 0.00002))::json AS g
        FROM assets a
        JOIN LATERAL (SELECT geom FROM boundary_versions bv WHERE bv.asset_id = a.id AND bv.kind IN ('ftl','parcel')
                      ORDER BY bv.version DESC LIMIT 1) b ON true
        """)).mappings().all()
    pts = [c for r in rows for poly in (r["g"]["coordinates"] if r["g"]["type"] == "MultiPolygon" else [r["g"]["coordinates"]]) for c in poly[0]]
    if not pts:
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"></svg>'
    w, e = min(p[0] for p in pts), max(p[0] for p in pts)
    s, n = min(p[1] for p in pts), max(p[1] for p in pts)
    kx = math.cos(math.radians((s + n) / 2))
    pad = 24
    scale = min((width - 2 * pad) / max((e - w) * kx, 1e-9), (height - 2 * pad) / max(n - s, 1e-9))
    ox = (width - (e - w) * kx * scale) / 2
    oy = (height - (n - s) * scale) / 2

    def xy(lon: float, lat: float) -> str:
        return f"{ox + (lon - w) * kx * scale:.1f},{oy + (n - lat) * scale:.1f}"

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="Map of watched assets">',
             f'<rect width="{width}" height="{height}" fill="#f0ece2"/>']
    for r in rows:
        polys = r["g"]["coordinates"] if r["g"]["type"] == "MultiPolygon" else [r["g"]["coordinates"]]
        fill = "#a4cae6" if r["type"] == "lake" else "#e6dcc2"
        for poly in polys:
            d = " ".join(xy(*c) for c in poly[0])
            parts.append(f'<polygon points="{d}" fill="{fill}" stroke="#1f6fa8" stroke-width="1"><title>{escape(r["name"])}</title></polygon>')
    for p in stats["new_alert_points"]:
        x, y = xy(p["lon"], p["lat"]).split(",")
        parts.append(f'<circle cx="{x}" cy="{y}" r="6" fill="#b07219" stroke="#fff" stroke-width="2"><title>{escape(p["code"])}</title></circle>')
    for o in stats["waiting"]:
        x, y = xy(o["lon"], o["lat"]).split(",")
        parts.append(f'<circle cx="{x}" cy="{y}" r="10" fill="none" stroke="#c4402f" stroke-width="2.5"><title>{escape(o["code"])} waiting</title></circle>')
    parts.append("</svg>")
    return "".join(parts)


def render_pdf(stats: dict, svg: str) -> bytes:
    from weasyprint import HTML

    ctx = {
        **stats,
        "label": month_label(stats["month"]),
        "last_label": month_label(stats["last_month"]["month"]),
        "map_uri": "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode(),
        "waiting_shown": stats["waiting"][:8],
        "waiting_more": max(0, len(stats["waiting"]) - 8),
        "state_labels": {"OPEN": "Open, not yet reviewed", "UNDER_REVIEW": "Under review"},
        "change_labels": {"building": "Construction", "small_structure": "Construction", "soil_fill": "Land fill",
                          "levelling": "Levelling", "clearing": "Clearing", "other": "Other change"},
        "fonts": {"regular": (FONTS / "NotoSans-Regular.ttf").as_uri(), "bold": (FONTS / "NotoSans-Bold.ttf").as_uri()},
    }
    return HTML(string=_env.get_template("monthly.html").render(**ctx), base_url=str(TEMPLATES)).write_pdf()
