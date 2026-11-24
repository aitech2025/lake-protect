"""Build pitch/theme.css from theme.src.css: inline the fonts and the Lucide icons the deck uses.

Usage: py -I pitch/build/build_theme.py <node_modules dir>
The node_modules dir needs lucide-static@0.460.0, @fontsource/inter@5.1.0, @fontsource/manrope@5.1.0.
"""
import base64
import re
import sys
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
PITCH = HERE.parent
NM = Path(sys.argv[1])

FONTS = [
    ("Inter", 400, "@fontsource/inter/files/inter-latin-400-normal.woff2"),
    ("Inter", 500, "@fontsource/inter/files/inter-latin-500-normal.woff2"),
    ("Inter", 600, "@fontsource/inter/files/inter-latin-600-normal.woff2"),
    ("Inter", 700, "@fontsource/inter/files/inter-latin-700-normal.woff2"),
    ("Manrope", 600, "@fontsource/manrope/files/manrope-latin-600-normal.woff2"),
    ("Manrope", 700, "@fontsource/manrope/files/manrope-latin-700-normal.woff2"),
    ("Manrope", 800, "@fontsource/manrope/files/manrope-latin-800-normal.woff2"),
]

# The product's own mark: a lake outline inside a dashed buffer ring, as in the app.
LOGO = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 44 30'>"
    "<ellipse cx='22' cy='15' rx='20' ry='13' fill='none' stroke='#e05a4f' stroke-width='2.2' stroke-dasharray='3.2 2.6'/>"
    "<ellipse cx='22' cy='15' rx='14.5' ry='8.5' fill='#8fcbee' stroke='#2f80c9' stroke-width='2.4'/>"
    "</svg>"
)


def data_uri(svg: str) -> str:
    return "url(\"data:image/svg+xml;utf8," + urllib.parse.quote(svg, safe="/:=' ") + "\")"


def main() -> None:
    css = (HERE / "theme.src.css").read_text(encoding="utf-8")
    faces = []
    for family, weight, rel in FONTS:
        b64 = base64.b64encode((NM / rel).read_bytes()).decode()
        faces.append(
            f"@font-face {{ font-family: '{family}'; font-weight: {weight}; font-style: normal; "
            f"font-display: block; src: url(data:font/woff2;base64,{b64}) format('woff2'); }}"
        )
    deck = (PITCH / "pitch-deck.md").read_text(encoding="utf-8")
    names = sorted(set(re.findall(r"\bic-([a-z0-9-]+)", deck)))
    rules = []
    missing = []
    for name in names:
        f = NM / "lucide-static" / "icons" / f"{name}.svg"
        if not f.exists():
            missing.append(name)
            continue
        svg = f.read_text(encoding="utf-8")
        svg = re.sub(r"<!--.*?-->", "", svg, flags=re.S)
        svg = re.sub(r"\s+", " ", svg).strip().replace('"', "'")
        svg = svg.replace("stroke='currentColor'", "stroke='black'")
        rules.append(f".ic-{name} {{ --i: {data_uri(svg)}; }}")
    if missing:
        sys.exit(f"Missing Lucide icons: {', '.join(missing)}")
    css = css.replace("/*FONTS*/", "\n".join(faces))
    css = css.replace("/*ICONS*/", "\n".join(rules))
    css = css.replace(":root {", f":root {{\n  --logo: {data_uri(LOGO)};", 1)
    (PITCH / "theme.css").write_text(css, encoding="utf-8", newline="\n")
    print(f"theme.css: {len(faces)} fonts, {len(rules)} icons, {len(css) // 1024} KB")


if __name__ == "__main__":
    main()
