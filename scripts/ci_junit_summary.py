#!/usr/bin/env python3
"""Append a compact pytest JUnit result and failing test names to GitHub's job summary."""
from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

report = Path(sys.argv[1])
label = sys.argv[2] if len(sys.argv) > 2 else "Tests"
lines = [f"## {label} test results"]
if not report.exists():
    lines.append(f"JUnit report not produced: `{report}`")
else:
    root = ET.parse(report).getroot()
    cases = list(root.iter("testcase"))
    failures = [node for case in cases for node in (*case.findall("failure"), *case.findall("error"))]
    skipped = [node for case in cases for node in case.findall("skipped")]
    lines.append(f"- Tests: **{len(cases)}**")
    lines.append(f"- Failed/errors: **{len(failures)}**")
    lines.append(f"- Skipped: **{len(skipped)}**")
    if failures:
        lines.append("")
        lines.append("### Failing tests")
        for case in cases:
            problems = [*case.findall("failure"), *case.findall("error")]
            if problems:
                classname = case.attrib.get("classname", "")
                name = case.attrib.get("name", "unknown")
                message = (problems[0].attrib.get("message") or problems[0].text or "").strip().splitlines()
                lines.append(f"- `{classname}::{name}` — {(message[0] if message else 'failure')[:300]}")
with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
    summary.write("\n".join(lines) + "\n")
