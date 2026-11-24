"""Fictional legal documents for the demo world: one-page PDFs, each marked as demo data.

They stand in for the notification, recovery order, court order and land records a real asset
would carry (DECISIONS.md D-057). Every name, number and date in them is invented.
"""
from __future__ import annotations


def _esc(line: str) -> str:
    return line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def simple_pdf(title: str, lines: list[str]) -> bytes:
    """A valid one-page A4 PDF in Helvetica. Text must be plain ASCII."""
    body = [f"BT /F2 15 Tf 56 790 Td ({_esc(title)}) Tj ET",
            "1 0 0 rg BT /F2 10 Tf 56 768 Td (DEMO DATA: FICTIONAL DOCUMENT. NOT A GOVERNMENT RECORD.) Tj ET 0 0 0 rg",
            "BT /F1 11 Tf 56 740 Td 16 TL " + " ".join(f"({_esc(line)}) Tj T*" for line in lines) + " ET"]
    content = "\n".join(body)
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(content.encode('latin-1'))} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for n, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{n} 0 obj\n{obj}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


def documents_for(asset: dict, cohort: str, boundary_date: str, court_case: dict | None) -> list[dict]:
    """The demo documents one asset carries, by its cohort and records."""
    name, key = asset["name"], asset["key"]
    survey = ", ".join(asset.get("survey") or []) or "none recorded"
    docs = []
    if cohort == "A_RECOVERED":
        ref = f"DEMO/RECOVERY/{key.upper()}"
        docs.append({"doc_type": "recovery_order", "title": f"Recovery order {ref}", "reference": ref, "issued_on": boundary_date,
                     "issued_by": "Demo Asset Protection Agency", "pdf": ["Order recovering the land and marking its boundary.",
                     f"Asset: {name}", f"Survey numbers: {survey}", f"Boundary marked on the ground on {boundary_date}.",
                     "The land is government land and stays under watch."]})
    if cohort in ("B_FINAL", "C_PRELIM") and asset.get("ref"):
        kind = "Final" if cohort == "B_FINAL" else "Preliminary"
        docs.append({"doc_type": "notification", "title": f"{kind} FTL notification {asset['ref']}", "reference": asset["ref"],
                     "issued_on": boundary_date, "issued_by": "Demo Lake Protection Committee", "pdf": [
                     f"{kind} notification of the Full Tank Level (FTL) of {name}.", f"Survey numbers: {survey}",
                     "Buffer zone: 30 m from the FTL for lakes of 10 ha or more, 9 m below (demo rule).",
                     "Claims and objections: " + ("closed." if kind == "Final" else "open for 30 days.")]})
    if cohort == "D_UNNOTIFIED":
        docs.append({"doc_type": "survey_map", "title": "Derived outline from imagery (not a notification)", "reference": None,
                     "issued_on": boundary_date, "issued_by": "Demo Survey Office", "pdf": [
                     f"Outline of {name} drawn from imagery.", "Not notified. Watch only until the committee notifies it."]})
    docs.append({"doc_type": "land_record", "title": "Record of Rights extract (land category, no names)", "reference": f"DEMO/ROR/{key.upper()}",
                 "issued_on": boundary_date, "issued_by": "Demo Revenue Office", "pdf": [
                 f"Survey numbers: {survey}", "Land category: government (tank bed and shikam).",
                 "Owner names are not held in Lake Protect."]})
    if court_case:
        docs.append({"doc_type": "court_order", "title": f"Court case {court_case['case_no']}", "reference": court_case["case_no"],
                     "issued_on": None, "issued_by": court_case["court"], "pdf": None})
    return docs
