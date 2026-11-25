"""What each notification says, in English and Telugu (DECISIONS.md D-059).

Every message names the incident, the asset and its area, says plainly what changed, and links
to the desk. It never names an owner or claimant, never says whether a change is lawful, and
never tells anyone what action to take on the ground: the official reviews the images and the
admin decides. Telugu strings are drafts for review by a native speaker.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from app.config import settings
from app.services.alert_view import CHANGE_LABEL, ZONE_LABEL

CHANGE_TE = {
    "building": "నిర్మాణం",
    "small_structure": "నిర్మాణం (చిన్న కట్టడం)",
    "soil_fill": "మట్టి నింపడం",
    "levelling": "నేల చదును చేయడం",
    "clearing": "చెట్లు తొలగించడం",
    "water_loss": "నీరు తగ్గడం",
    "other": "ఇతర మార్పు",
}
ZONE_TE = {
    "inside_ftl": "హద్దు లోపల",
    "buffer": "బఫర్ జోన్‌లో",
    "watch_ring": "100 మీ. పరిశీలన వలయంలో",
    "outside": "పరిశీలన పరిధి బయట",
}
DECISION = {
    "en": {"CONFIRMED": "confirmed as a real change", "DISMISSED": "dismissed as not a real change"},
    "te": {"CONFIRMED": "నిజమైన మార్పుగా నిర్ధారించబడింది", "DISMISSED": "నిజమైన మార్పు కాదని తోసిపుచ్చబడింది"},
}

TEXT = {
    "en": {
        "incident_opened.subject": "New incident {code}: {change} at {asset}",
        "incident_opened.body": "{summary}.\n\nAsset: {asset}, {area}.\nIncident {code}, opened {opened}.\n{flags}"
                                "Please look at the images, record your review and acknowledge this message:\n{link}",
        "incident_opened.unrouted": "No official covers this area yet. Set one on the Officials page.\n",
        "incident_decided.subject": "Incident {code} {decision}: {asset}",
        "incident_decided.body": "The admin has {decision} incident {code} at {asset}, {area}.\n{summary}.\n\nThe admin's note: {note}\n{link}",
        "reminder.subject": "Reminder: incident {code} at {asset} is waiting for you",
        "reminder.body": "You were notified on {notified} and have not acknowledged it yet.\n\n{summary}.\nAsset: {asset}, {area}.\n{link}",
        "not_acknowledged.subject": "{official} has not acknowledged incident {code}",
        "not_acknowledged.body": "{official} was notified on {notified} about incident {code} at {asset}, {area}, "
                                 "and has not acknowledged it within 48 hours.\n\n{summary}.\n{link}",
        "flag.court": "A court case is recorded on this asset: the legal team should see it before anyone acts.\n",
        "flag.boundary": "The boundary is not confirmed: treat the zone as an estimate.\n",
        "area.none": "area not recorded",
        "weekly_digest.subject": "Week {week}: change at {changed} assets, {new} new incidents, {waiting} waiting for you",
        "digest.scope": "Week {week} ({dates}), {scope}.",
        "digest.scope_all": "all areas",
        "digest.scope_areas": "your area: {areas}",
        "digest.watched": "{watched} locations watched: {clear} seen clearly, {no_clear} without a clear look.",
        "digest.no_clear": "No clear look this week: {names}.",
        "digest.changes": "Changes found this week:",
        "digest.change": "- {asset}: {change} of about {area_sq_m:,.0f} sq m, incident {code}{continues}",
        "digest.continues": " (seen again)",
        "digest.no_changes": "No change found this week where the look was clear.",
        "digest.new": "New incidents this week: {count}.",
        "digest.waiting_viewer": "Waiting for your review: {count}.",
        "digest.waiting_admin": "Waiting for your decision: {count}.",
        "digest.waiting_item": "- {code} at {asset}, open {days} days",
        "digest.old": "Open for more than 14 days: {count}.",
        "digest.link": "Open the desk: {link}",
    },
    "te": {
        "incident_opened.subject": "కొత్త సంఘటన {code}: {asset} వద్ద {change}",
        "incident_opened.body": "{summary}.\n\nఆస్తి: {asset}, {area}.\nసంఘటన {code}, {opened} న తెరవబడింది.\n{flags}"
                                "దయచేసి చిత్రాలను చూసి, మీ పరిశీలనను నమోదు చేసి, ఈ సందేశం అందినట్లు నిర్ధారించండి:\n{link}",
        "incident_opened.unrouted": "ఈ ప్రాంతానికి ఇంకా అధికారి లేరు. అధికారుల పేజీలో ఒకరిని నియమించండి.\n",
        "incident_decided.subject": "సంఘటన {code} {decision}: {asset}",
        "incident_decided.body": "{asset}, {area} వద్ద సంఘటన {code} {decision}.\n{summary}.\n\nనిర్వాహకుల గమనిక: {note}\n{link}",
        "reminder.subject": "గుర్తు: {asset} వద్ద సంఘటన {code} మీ కోసం వేచి ఉంది",
        "reminder.body": "మీకు {notified} న తెలియజేశాం; ఇంకా అందినట్లు నిర్ధారించలేదు.\n\n{summary}.\nఆస్తి: {asset}, {area}.\n{link}",
        "not_acknowledged.subject": "{official} సంఘటన {code} అందినట్లు నిర్ధారించలేదు",
        "not_acknowledged.body": "{asset}, {area} వద్ద సంఘటన {code} గురించి {official} కు {notified} న తెలియజేశాం; "
                                 "48 గంటల్లో అందినట్లు నిర్ధారించలేదు.\n\n{summary}.\n{link}",
        "flag.court": "ఈ ఆస్తిపై కోర్టు కేసు నమోదై ఉంది: ఎవరైనా చర్య తీసుకునే ముందు న్యాయ బృందం చూడాలి.\n",
        "flag.boundary": "సరిహద్దు నిర్ధారించబడలేదు: జోన్‌ను అంచనాగా మాత్రమే చూడండి.\n",
        "area.none": "ప్రాంతం నమోదు కాలేదు",
        "weekly_digest.subject": "వారం {week}: {changed} చోట్ల మార్పులు, {new} కొత్త సంఘటనలు, {waiting} మీ కోసం వేచి ఉన్నాయి",
        "digest.scope": "వారం {week} ({dates}), {scope}.",
        "digest.scope_all": "అన్ని ప్రాంతాలు",
        "digest.scope_areas": "మీ ప్రాంతం: {areas}",
        "digest.watched": "{watched} ప్రదేశాలు పరిశీలనలో: {clear} స్పష్టంగా కనిపించాయి, {no_clear} స్పష్టంగా కనిపించలేదు.",
        "digest.no_clear": "ఈ వారం స్పష్టమైన చిత్రం లేదు: {names}.",
        "digest.changes": "ఈ వారం కనిపించిన మార్పులు:",
        "digest.change": "- {asset}: సుమారు {area_sq_m:,.0f} చ.మీ. {change}, సంఘటన {code}{continues}",
        "digest.continues": " (మళ్ళీ కనిపించింది)",
        "digest.no_changes": "స్పష్టంగా కనిపించిన చోట్ల ఈ వారం మార్పు లేదు.",
        "digest.new": "ఈ వారం కొత్త సంఘటనలు: {count}.",
        "digest.waiting_viewer": "మీ పరిశీలన కోసం వేచి ఉన్నవి: {count}.",
        "digest.waiting_admin": "మీ నిర్ణయం కోసం వేచి ఉన్నవి: {count}.",
        "digest.waiting_item": "- {asset} వద్ద {code}, {days} రోజులుగా తెరిచి ఉంది",
        "digest.old": "14 రోజులకు పైగా తెరిచి ఉన్నవి: {count}.",
        "digest.link": "డెస్క్ తెరవండి: {link}",
    },
}


@dataclass(frozen=True)
class Message:
    subject: str
    body: str


def lang(user_language: str | None) -> str:
    return "te" if user_language == "te" else "en"


def t(language: str, key: str, **values) -> str:
    return TEXT[lang(language)][key].format(**values)


def link(path: str) -> str:
    return settings.public_url.rstrip("/") + path


def area_text(area: dict | None, language: str) -> str:
    area = area or {}
    parts = [area.get(k) for k in ("village", "mandal", "district") if area.get(k)]
    return ", ".join(parts) if parts else TEXT[lang(language)]["area.none"]


def summary(p: dict, language: str) -> str:
    """The incident's plain sentence; in Telugu from Telugu labels, so no English is mixed in."""
    if lang(language) == "en":
        return p["summary"]
    what = CHANGE_TE.get(p["change_type"], "మార్పు")
    size = f"సుమారు {p['area_sq_m']:,.0f} చ.మీ. " if p.get("area_sq_m") else ""
    where = f", {ZONE_TE[p['zone']]}" if p.get("zone") in ZONE_TE else ""
    when = f", మొదట {p['first_changed_at']} న కనిపించింది" if p.get("first_changed_at") else ""
    return f"{size}{what}{where}{when}"


def _date(value) -> str:
    if isinstance(value, str):
        value = dt.datetime.fromisoformat(value)
    return f"{value:%d %b %Y}"


def incident_payload(row: dict) -> dict:
    """The facts every incident notification carries, from the incident's list row."""
    return {
        "alert_id": row["id"],
        "code": row["code"],
        "asset_id": row["asset_id"],
        "asset_name": row["asset_name"],
        "asset_name_te": row["asset_name_te"],
        "area": {k: row.get(k) for k in ("district", "mandal", "village")},
        "change_type": row["change_type"],
        "change_label": CHANGE_LABEL.get(row["change_type"], row["change_type"]),
        "zone": row["zone"],
        "zone_label": ZONE_LABEL.get(row["zone"] or "", ""),
        "area_sq_m": row["area_sq_m"],
        "first_changed_at": row["first_changed_at"].isoformat() if row["first_changed_at"] else None,
        "summary": row["summary"],
        "state": row["state"],
        "court_matter": row["court_matter"],
        "boundary_confirmed": row["boundary_confirmed"],
        "opened_at": row["created_at"].isoformat(),
        "link": link(f"/alerts/{row['id']}"),
    }


def compose(kind: str, language: str, p: dict) -> Message:
    language = lang(language)
    if kind == "weekly_digest":
        return digest_message(language, p)
    if kind == "citizen_report" or p.get("report"):
        return report_message(kind, language, p)
    asset = (p.get("asset_name_te") or p["asset_name"]) if language == "te" else p["asset_name"]
    change = CHANGE_TE.get(p["change_type"], p["change_label"]) if language == "te" else p["change_label"]
    values = {
        "code": p["code"], "asset": asset, "change": change, "area": area_text(p.get("area"), language),
        "summary": summary(p, language), "link": p["link"], "opened": _date(p["opened_at"]),
    }
    if kind == "incident_opened":
        flags = ""
        if p.get("court_matter"):
            flags += t(language, "flag.court")
        if not p.get("boundary_confirmed"):
            flags += t(language, "flag.boundary")
        if p.get("unrouted"):
            flags += t(language, "incident_opened.unrouted")
        return Message(t(language, "incident_opened.subject", **values), t(language, "incident_opened.body", flags=flags, **values))
    if kind == "incident_decided":
        decision = DECISION[language][p["decision"]]
        return Message(t(language, "incident_decided.subject", decision=decision, **values),
                       t(language, "incident_decided.body", decision=decision, note=p.get("note") or "", **values))
    if kind == "reminder":
        return Message(t(language, "reminder.subject", **values),
                       t(language, "reminder.body", notified=_date(p["notified_at"]), **values))
    if kind == "not_acknowledged":
        return Message(t(language, "not_acknowledged.subject", official=p["official_name"], **values),
                       t(language, "not_acknowledged.body", official=p["official_name"], notified=_date(p["notified_at"]), **values))
    raise ValueError(f"Unknown notification kind {kind}")


REPORT_TEXT = {
    "en": {
        "subject": "Citizen report {code}: {what} at {asset}",
        "body": "A citizen reported: {what}.\nPlace: {asset}, {area}.\n{description}Received by {channel} on {opened}.\n{flags}"
                "Please check it against the satellite images and records, record your check and acknowledge this message:\n{link}",
        "reminder.subject": "Reminder: citizen report {code} at {asset} is waiting for you",
        "reminder.body": "You were notified on {notified} and have not acknowledged it yet.\n\n{what}.\nPlace: {asset}, {area}.\n{link}",
        "not_acknowledged.subject": "{official} has not acknowledged citizen report {code}",
        "not_acknowledged.body": "{official} was notified on {notified} about citizen report {code} at {asset}, {area}, "
                                 "and has not acknowledged it within 48 hours.\n{link}",
        "description": "In their words: \"{text}\"\n",
        "flag.incident": "It is next to incident {incident}, which is open.\n",
        "flag.not_watched": "The place is not on the watch list: add it as a location, or pass the report to the right department.\n",
        "flag.no_place": "No pin was given: place it from the description.\n",
        "flag.repeat_false": "Earlier reports from the same source were closed as false.\n",
    },
    "te": {
        "subject": "పౌరుల సమాచారం {code}: {asset} వద్ద {what}",
        "body": "ఒక పౌరుడు తెలిపారు: {what}.\nప్రదేశం: {asset}, {area}.\n{description}{opened} న {channel} ద్వారా అందింది.\n{flags}"
                "దయచేసి ఉపగ్రహ చిత్రాలు, రికార్డులతో పరిశీలించి, మీ పరిశీలనను నమోదు చేసి, ఈ సందేశం అందినట్లు నిర్ధారించండి:\n{link}",
        "reminder.subject": "గుర్తు: {asset} వద్ద పౌరుల సమాచారం {code} మీ కోసం వేచి ఉంది",
        "reminder.body": "మీకు {notified} న తెలియజేశాం; ఇంకా అందినట్లు నిర్ధారించలేదు.\n\n{what}.\nప్రదేశం: {asset}, {area}.\n{link}",
        "not_acknowledged.subject": "{official} పౌరుల సమాచారం {code} అందినట్లు నిర్ధారించలేదు",
        "not_acknowledged.body": "{asset}, {area} వద్ద పౌరుల సమాచారం {code} గురించి {official} కు {notified} న తెలియజేశాం; "
                                 "48 గంటల్లో అందినట్లు నిర్ధారించలేదు.\n{link}",
        "description": "వారి మాటల్లో: \"{text}\"\n",
        "flag.incident": "ఇది తెరిచి ఉన్న సంఘటన {incident} పక్కనే ఉంది.\n",
        "flag.not_watched": "ఈ ప్రదేశం పరిశీలన జాబితాలో లేదు: దాన్ని ప్రదేశంగా చేర్చండి, లేదా సంబంధిత శాఖకు పంపండి.\n",
        "flag.no_place": "పిన్ ఇవ్వలేదు: వివరణ ఆధారంగా ప్రదేశాన్ని గుర్తించండి.\n",
        "flag.repeat_false": "ఇదే మూలం నుండి వచ్చిన గత సమాచారాలు తప్పుడువిగా ముగిశాయి.\n",
    },
}


def report_message(kind: str, language: str, p: dict) -> Message:
    from app.citizen import texts as ctexts

    tx = REPORT_TEXT[language]
    asset = (p.get("asset_name_te") or p["asset_name"]) if language == "te" else p["asset_name"]
    what = p.get("what_te") if language == "te" else p["what_label"]
    values = {"code": p["code"], "asset": asset, "what": what, "area": area_text(p.get("area"), language), "link": p["link"],
              "opened": _date(p["opened_at"]), "channel": ctexts.pick(ctexts.CHANNEL.get(p.get("channel"), {"en": p.get("channel", "")}), language)}
    if kind == "citizen_report":
        flags = ""
        if p.get("incident_code"):
            flags += tx["flag.incident"].format(incident=p["incident_code"])
        if p.get("not_watched") and not p.get("no_place"):
            flags += tx["flag.not_watched"]
        if p.get("no_place"):
            flags += tx["flag.no_place"]
        if p.get("repeat_false"):
            flags += tx["flag.repeat_false"]
        if p.get("unrouted") and not p.get("not_watched"):
            flags += t(language, "incident_opened.unrouted")
        description = tx["description"].format(text=p["description"]) if p.get("description") else ""
        return Message(tx["subject"].format(**values), tx["body"].format(flags=flags, description=description, **values))
    if kind == "reminder":
        return Message(tx["reminder.subject"].format(**values), tx["reminder.body"].format(notified=_date(p["notified_at"]), **values))
    if kind == "not_acknowledged":
        return Message(tx["not_acknowledged.subject"].format(official=p["official_name"], **values),
                       tx["not_acknowledged.body"].format(official=p["official_name"], notified=_date(p["notified_at"]), **values))
    raise ValueError(f"Unknown notification kind {kind}")


def digest_message(language: str, d: dict) -> Message:
    f = d["figures"]
    names = lambda items: ", ".join((i.get("asset_name_te") or i["asset_name"]) if language == "te" else i["asset_name"] for i in items)  # noqa: E731
    scope = t(language, "digest.scope_all") if d["scope"] == "all" else t(language, "digest.scope_areas", areas="; ".join(d["areas"]))
    lines = [
        t(language, "digest.scope", week=d["week"], dates=f"{_date(d['from'])} to {_date(d['to'])}", scope=scope),
        t(language, "digest.watched", watched=f["watched"], clear=f["clear_look"], no_clear=f["no_clear_look"]),
    ]
    if d["no_clear_look"]:
        lines.append(t(language, "digest.no_clear", names=names(d["no_clear_look"])))
    lines.append("")
    if d["changes"]:
        lines.append(t(language, "digest.changes"))
        for c in d["changes"]:
            asset = (c.get("asset_name_te") or c["asset_name"]) if language == "te" else c["asset_name"]
            change = CHANGE_TE.get(c["change_type"], c["change_label"]) if language == "te" else c["change_label"]
            lines.append(t(language, "digest.change", asset=asset, change=change, area_sq_m=c["area_sq_m"] or 0,
                           code=c.get("alert_code") or "-", continues=t(language, "digest.continues") if c.get("continues") else ""))
    else:
        lines.append(t(language, "digest.no_changes"))
    lines += ["", t(language, "digest.new", count=f["new_incidents"])]
    lines.append(t(language, "digest.waiting_admin" if d["role"] == "admin" else "digest.waiting_viewer", count=f["waiting_for_you"]))
    for w in d["waiting"][:10]:
        asset = (w.get("asset_name_te") or w["asset_name"]) if language == "te" else w["asset_name"]
        lines.append(t(language, "digest.waiting_item", code=w["code"], asset=asset, days=w["days_open"]))
    lines.append(t(language, "digest.old", count=f["open_over_14_days"]))
    lines += ["", t(language, "digest.link", link=d["link"])]
    subject = t(language, "weekly_digest.subject", week=d["week"], changed=f["changed"], new=f["new_incidents"], waiting=f["waiting_for_you"])
    return Message(subject, "\n".join(lines))
