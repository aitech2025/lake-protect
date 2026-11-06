"""Invariant 11: no English or Telugu string uses a banned word from section 6.8.

Scans every user-facing text source in the repository: API string literals and templates, rule
configuration, database trigger messages, and the web app's sources and i18n files. New text
sources are picked up automatically by extension.
"""
import ast
import re
from pathlib import Path

import pytest

from app.config import settings

REPO = Path(settings.repo_dir)

BANNED_EN = [
    r"\bviolations?\b",
    r"\billegal(ly|ity)?\b",
    r"\bunauthori[sz]ed\b",
    r"\bproof of encroachment\b",
    r"\bencroachers?\b",
    r"\bland[\s-]?grabb(er|ers|ing)\b",
    r"\bdemolish\w*",
    r"\bdemolitions?\b",
]
# Telugu stems for the same ideas: violation, illegal (two forms), unauthorised, encroacher,
# land grab (kabja), demolish or demolition, proof of encroachment.
BANNED_TE = ["ఉల్లంఘన", "అక్రమ", "చట్టవిరుద్ధ", "అనధికార", "ఆక్రమణదారు", "కబ్జా", "కూల్చ", "ఆక్రమణకు రుజువు"]
PATTERN = re.compile("|".join(BANNED_EN + [re.escape(t) for t in BANNED_TE]), re.IGNORECASE)

SKIP_DIRS = {"node_modules", "dist", "dev-dist", "__pycache__", "tests", "test-results", "playwright-report"}


def _python_strings(path: Path) -> list[str]:
    return [n.value for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def _sources() -> list[Path]:
    roots = [REPO / "api" / "app", REPO / "api" / "migrations", REPO / "web" / "src", REPO / "web" / "public", REPO / "data" / "demo"]
    exts = {".py", ".html", ".yaml", ".yml", ".json", ".ts", ".tsx", ".css", ".md", ".csv", ".svg"}
    found = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.is_file() and p.suffix in exts and not (SKIP_DIRS & set(p.parts)):
                found.append(p)
    return found


def test_scan_covers_the_text_sources():
    names = {p.name for p in _sources()}
    assert {"config.yaml", "state_machine.py", "0002_data_model.py"} <= names


@pytest.mark.parametrize("path", _sources(), ids=lambda p: str(p.relative_to(REPO)))
def test_invariant_11_no_banned_words(path: Path):
    texts = _python_strings(path) if path.suffix == ".py" else [path.read_text(encoding="utf-8", errors="ignore")]
    hits = sorted({m.group(0) for t in texts for m in PATTERN.finditer(t)})
    assert hits == [], f"{path.relative_to(REPO)} uses banned wording: {hits}"


def test_pattern_catches_each_banned_word():
    for sample in ["violation", "Illegal", "unauthorised", "proof of encroachment", "encroacher", "land grabber", "demolish", "demolition",
                   "ఉల్లంఘన", "అక్రమ నిర్మాణం", "కూల్చివేత"]:
        assert PATTERN.search(sample), sample
    assert not PATTERN.search("Imagery shows physical change. It does not establish title or legality.")
