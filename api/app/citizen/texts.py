"""What citizens read, in English and Telugu (CONTEXT.md 17.8; DECISIONS.md D-062, D-063).

Plain words. A note never names an officer, an owner or a claimant, never shows evidence, and never
says whether anyone broke the law. The Telugu is a draft for review by a native speaker.
"""
from __future__ import annotations

LANGS = ("en", "te")

WHAT = {
    "dumping": {"en": "Soil or debris being dumped", "te": "మట్టి లేదా వ్యర్థాలు పోస్తున్నారు"},
    "construction": {"en": "Building or construction", "te": "భవనం లేదా నిర్మాణం"},
    "fencing": {"en": "Fence, wall or boundary stones", "te": "కంచె, గోడ లేదా హద్దు రాళ్లు"},
    "clearing": {"en": "Trees cleared or land levelled", "te": "చెట్లు తొలగించి, భూమిని చదును చేశారు"},
    "other": {"en": "Something else", "te": "ఇంకేదైనా"},
}

STATUS = {
    "RECEIVED": {"en": "Received", "te": "అందింది"},
    "CHECKING": {"en": "Being checked", "te": "పరిశీలనలో ఉంది"},
    "CLOSED": {"en": "Closed", "te": "ముగిసింది"},
}

CHANNEL = {
    "web": {"en": "web portal", "te": "వెబ్ పోర్టల్"},
    "whatsapp": {"en": "WhatsApp", "te": "WhatsApp"},
    "helpline_1070": {"en": "1070 helpline", "te": "1070 హెల్ప్‌లైన్"},
    "praja_vani": {"en": "Praja Vani", "te": "ప్రజావాణి"},
    "walk_in": {"en": "in person", "te": "నేరుగా"},
}

DEPARTMENTS = {
    "revenue": {"en": "the Revenue Department (Tahsildar)", "te": "రెవెన్యూ శాఖ (తహసీల్దార్)"},
    "municipal": {"en": "the municipality (GHMC or the local body)", "te": "పురపాలక సంస్థ (GHMC లేదా స్థానిక సంస్థ)"},
    "irrigation": {"en": "the Irrigation Department", "te": "నీటిపారుదల శాఖ"},
    "hydraa": {"en": "HYDRAA", "te": "హైడ్రా"},
    "forest": {"en": "the Forest Department", "te": "అటవీ శాఖ"},
    "endowments": {"en": "the Endowments Department", "te": "దేవాదాయ శాఖ"},
    "waqf": {"en": "the Telangana Waqf Board", "te": "తెలంగాణ వక్ఫ్ బోర్డు"},
}

# Notes the citizen sees on each step. {ref}, {place}, {date} and {department} are filled in.
NOTES = {
    "received": {
        "en": "We received your report. Your reference is {ref}.",
        "te": "మీరు పంపిన సమాచారం అందింది. మీ సూచిక సంఖ్య {ref}.",
    },
    "case_opened": {
        "en": "Officials have opened a case for this place. The app is checking it against satellite images.",
        "te": "ఈ ప్రదేశంపై అధికారులు కేసు తెరిచారు. యాప్ దీన్ని ఉపగ్రహ చిత్రాలతో పరిశీలిస్తోంది.",
    },
    "placed_from_words": {
        "en": "We found the place from your words: {place}.",
        "te": "మీ మాటల నుండి ప్రదేశాన్ని గుర్తించాం: {place}.",
    },
    "review_change": {
        "en": "The newest satellite images show a change at this place, first seen {date}. Officials have been told.",
        "te": "తాజా ఉపగ్రహ చిత్రాల్లో ఈ ప్రదేశంలో మార్పు కనిపిస్తోంది, మొదట {date}న కనిపించింది. అధికారులకు తెలియజేశాం.",
    },
    "review_no_change": {
        "en": "Satellite images up to {date} show no change large enough to see from space. Small works may not show; officials will still look at it.",
        "te": "{date} వరకు ఉపగ్రహ చిత్రాల్లో అంతరిక్షం నుండి కనిపించేంత పెద్ద మార్పు లేదు. చిన్న పనులు కనిపించకపోవచ్చు; అధికారులు ఇంకా పరిశీలిస్తారు.",
    },
    "review_no_look": {
        "en": "There is no clear satellite image of this place yet, because of cloud. Officials will still look at it.",
        "te": "మేఘాల వల్ల ఈ ప్రదేశం స్పష్టమైన ఉపగ్రహ చిత్రం ఇంకా లేదు. అధికారులు ఇంకా పరిశీలిస్తారు.",
    },
    "under_review": {
        "en": "An official is reviewing it.",
        "te": "ఒక అధికారి దీన్ని సమీక్షిస్తున్నారు.",
    },
    "sharper_images": {
        "en": "Officials have asked for sharper satellite images of this place.",
        "te": "ఈ ప్రదేశం యొక్క మరింత స్పష్టమైన ఉపగ్రహ చిత్రాలను అధికారులు కోరారు.",
    },
    "added_to_watch": {
        "en": "This place is now on GeoGuard's weekly watch: {place}.",
        "te": "ఈ ప్రదేశం ఇప్పుడు GeoGuard వారపు పరిశీలనలో ఉంది: {place}.",
    },
    "linked_incident": {
        "en": "It matches a change officials are already reviewing at {place}.",
        "te": "{place} వద్ద అధికారులు ఇప్పటికే పరిశీలిస్తున్న మార్పుతో ఇది సరిపోలుతోంది.",
    },
    "duplicate": {
        "en": "Others reported the same place. You will get the same updates.",
        "te": "ఇదే ప్రదేశం గురించి ఇతరులు కూడా తెలిపారు. మీకూ అవే సమాచారాలు అందుతాయి.",
    },
    "no_place": {
        "en": "We need the exact place. Officials will find it from your description.",
        "te": "ఖచ్చితమైన ప్రదేశం కావాలి. మీ వివరణ ఆధారంగా అధికారులు దాన్ని గుర్తిస్తారు.",
    },
    "placed": {
        "en": "Officials found the place: {place}.",
        "te": "అధికారులు ప్రదేశాన్ని గుర్తించారు: {place}.",
    },
    "change_found": {
        "en": "The satellite images show a change at this place. Officials are reviewing it.",
        "te": "ఉపగ్రహ చిత్రాల్లో ఈ ప్రదేశంలో మార్పు కనిపించింది. అధికారులు దాన్ని పరిశీలిస్తున్నారు.",
    },
    "satellite_checked": {
        "en": "Satellite images up to {date} were checked: no change large enough to see from space yet. Small works may not show; officials will still look at your report.",
        "te": "{date} వరకు ఉపగ్రహ చిత్రాలను పరిశీలించాం: అంతరిక్షం నుండి కనిపించేంత పెద్ద మార్పు ఇంకా లేదు. చిన్న పనులు కనిపించకపోవచ్చు; అధికారులు మీ సమాచారాన్ని ఇంకా పరిశీలిస్తారు.",
    },
    # Closing, with the incident's decision.
    "incident_confirmed": {
        "en": "Closed: officials confirmed a change at this place. Action is with the department.",
        "te": "ముగిసింది: ఈ ప్రదేశంలో మార్పును అధికారులు నిర్ధారించారు. చర్య సంబంధిత శాఖ వద్ద ఉంది.",
    },
    "incident_dismissed": {
        "en": "Closed: officials reviewed this place and found no change that needs action. If the work continues, please report again with a new photo.",
        "te": "ముగిసింది: అధికారులు ఈ ప్రదేశాన్ని పరిశీలించారు; చర్య అవసరమైన మార్పు కనిపించలేదు. పని కొనసాగితే, కొత్త ఫోటోతో మళ్లీ తెలపండి.",
    },
    "passed_on": {
        "en": "Closed here: officials found this is for another department. Your report was passed to {department}.",
        "te": "ఇక్కడ ముగిసింది: ఇది మరో శాఖకు సంబంధించినదని అధికారులు గుర్తించారు. మీ సమాచారాన్ని {department}కు పంపాం.",
    },
}

PLACE_UNWATCHED = {"en": "a place not on the watch list", "te": "పరిశీలన జాబితాలో లేని ప్రదేశం"}

# The WhatsApp conversation.
BOT = {
    "welcome": (
        "GeoGuard: Telangana's weekly watch over lakes and government land.\n"
        "Reply with a number / సంఖ్యతో జవాబివ్వండి:\n"
        "1 English\n2 తెలుగు\n"
        "To check a report, send its reference, for example GGR-7K3M-9QXA."
    ),
    "ask_place": {
        "en": "Share the place: tap 📎, then Location, and send the pin. Or type the name of the lake or place, the village and the mandal.",
        "te": "ప్రదేశాన్ని పంపండి: 📎 నొక్కి, Location ఎంచుకుని పిన్ పంపండి. లేదా చెరువు లేదా ప్రదేశం పేరు, గ్రామం, మండలం టైప్ చేయండి.",
    },
    "ask_what": {"en": "What is happening there? Reply with a number:", "te": "అక్కడ ఏమి జరుగుతోంది? సంఖ్యతో జవాబివ్వండి:"},
    "ask_photo": {"en": "Send a photo of it, or reply SKIP.", "te": "దాని ఫోటో పంపండి, లేదా SKIP అని పంపండి."},
    "ask_describe": {
        "en": "Describe it in a few words, or reply SKIP. Please do not name any person.",
        "te": "కొన్ని మాటల్లో వివరించండి, లేదా SKIP అని పంపండి. దయచేసి ఎవరి పేరూ రాయకండి.",
    },
    "ask_updates": {
        "en": "Do you want updates on this WhatsApp number? Reply YES or NO.",
        "te": "ఈ WhatsApp నంబర్‌కు సమాచారం కావాలా? YES లేదా NO అని పంపండి.",
    },
    "done": {
        "en": "Thank you. {first}\nSend {ref} at any time to see its status.",
        "te": "ధన్యవాదాలు. {first}\nస్థితి తెలుసుకోవడానికి ఎప్పుడైనా {ref} పంపండి.",
    },
    "status": {"en": "Report {ref}: {status}.\n{note}", "te": "సమాచారం {ref}: {status}.\n{note}"},
    "not_found": {
        "en": "No report has that reference. Check it and send it again.",
        "te": "ఆ సూచిక సంఖ్యతో సమాచారం లేదు. సరిచూసి మళ్లీ పంపండి.",
    },
    "invalid": {"en": "Sorry, I did not understand.", "te": "క్షమించండి, అర్థం కాలేదు."},
    "outside": {
        "en": "That pin is outside Telangana. Please send the place again.",
        "te": "ఆ పిన్ తెలంగాణ బయట ఉంది. దయచేసి ప్రదేశాన్ని మళ్లీ పంపండి.",
    },
    "photo_kept": {"en": "Photo received.", "te": "ఫోటో అందింది."},
    "photo_not_fetched": {
        "en": "Photo noted. It could not be downloaded yet; officials will see that you sent one.",
        "te": "ఫోటో నమోదైంది. ఇంకా డౌన్‌లోడ్ కాలేదు; మీరు ఫోటో పంపినట్లు అధికారులకు తెలుస్తుంది.",
    },
    "too_many": {
        "en": "You have sent many reports today. Please try again tomorrow.",
        "te": "ఈ రోజు మీరు చాలా సమాచారాలు పంపారు. దయచేసి రేపు మళ్లీ ప్రయత్నించండి.",
    },
    "restart": {"en": "Send RESTART to start again.", "te": "మళ్లీ మొదలుపెట్టడానికి RESTART పంపండి."},
}
SKIP = {"skip", "వద్దు", "no photo"}
YES = {"yes", "y", "1", "అవును", "haan", "ha"}
NO = {"no", "n", "2", "కాదు", "వద్దు", "nahi"}
WHAT_ORDER = ("dumping", "construction", "fencing", "clearing", "other")

# How a citizen incident is described to officials (D-063).
REPORTED = {
    "dumping": {"en": "Soil or debris dumping", "te": "మట్టి లేదా వ్యర్థాలు పోయడం"},
    "construction": {"en": "Construction", "te": "నిర్మాణం"},
    "fencing": {"en": "A fence or wall", "te": "కంచె లేదా గోడ"},
    "clearing": {"en": "Clearing or levelling", "te": "చెట్ల తొలగింపు లేదా చదును"},
    "other": {"en": "A change", "te": "ఒక మార్పు"},
}


def pick(table: dict, language: str) -> str:
    return table.get(language) or table["en"]


def note(key: str, **values) -> dict:
    """A public note in both languages."""
    out = {}
    for lang in LANGS:
        v = {k: (pick(x, lang) if isinstance(x, dict) else x) for k, x in values.items()}
        out[lang] = NOTES[key][lang].format(**v)
    return out
