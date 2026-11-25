"""What citizens read, in English, Telugu and Urdu (CONTEXT.md 17.8; DECISIONS.md D-062).

Plain words. A note never names an officer, an owner or a claimant, never shows evidence, and never
says whether anyone broke the law. The Telugu and Urdu are drafts for review by native speakers.
"""
from __future__ import annotations

LANGS = ("en", "te", "ur")

WHAT = {
    "dumping": {"en": "Soil or debris being dumped", "te": "మట్టి లేదా వ్యర్థాలు పోస్తున్నారు", "ur": "مٹی یا ملبہ ڈالا جا رہا ہے"},
    "construction": {"en": "Building or construction", "te": "భవనం లేదా నిర్మాణం", "ur": "عمارت یا تعمیر"},
    "fencing": {"en": "Fence, wall or boundary stones", "te": "కంచె, గోడ లేదా హద్దు రాళ్లు", "ur": "باڑ، دیوار یا حد بندی کے پتھر"},
    "clearing": {"en": "Trees cleared or land levelled", "te": "చెట్లు తొలగించి, భూమిని చదును చేశారు", "ur": "درخت کاٹے گئے یا زمین ہموار کی گئی"},
    "other": {"en": "Something else", "te": "ఇంకేదైనా", "ur": "کچھ اور"},
}

STATUS = {
    "RECEIVED": {"en": "Received", "te": "అందింది", "ur": "موصول"},
    "CHECKING": {"en": "Being checked", "te": "పరిశీలనలో ఉంది", "ur": "جانچ جاری ہے"},
    "CLOSED": {"en": "Closed", "te": "ముగిసింది", "ur": "بند"},
}

CHANNEL = {
    "web": {"en": "web portal", "te": "వెబ్ పోర్టల్", "ur": "ویب پورٹل"},
    "whatsapp": {"en": "WhatsApp", "te": "WhatsApp", "ur": "واٹس ایپ"},
    "helpline_1070": {"en": "1070 helpline", "te": "1070 హెల్ప్‌లైన్", "ur": "1070 ہیلپ لائن"},
    "praja_vani": {"en": "Praja Vani", "te": "ప్రజావాణి", "ur": "پرجا وانی"},
    "walk_in": {"en": "in person", "te": "నేరుగా", "ur": "بذات خود"},
}

DEPARTMENTS = {
    "revenue": {"en": "the Revenue Department (Tahsildar)", "te": "రెవెన్యూ శాఖ (తహసీల్దార్)", "ur": "محکمہ مال (تحصیلدار)"},
    "municipal": {"en": "the municipality (GHMC or the local body)", "te": "పురపాలక సంస్థ (GHMC లేదా స్థానిక సంస్థ)", "ur": "بلدیہ (جی ایچ ایم سی یا مقامی ادارہ)"},
    "irrigation": {"en": "the Irrigation Department", "te": "నీటిపారుదల శాఖ", "ur": "محکمہ آبپاشی"},
    "hydraa": {"en": "HYDRAA", "te": "హైడ్రా", "ur": "حائیڈرا"},
    "forest": {"en": "the Forest Department", "te": "అటవీ శాఖ", "ur": "محکمہ جنگلات"},
    "endowments": {"en": "the Endowments Department", "te": "దేవాదాయ శాఖ", "ur": "محکمہ انڈومنٹس"},
    "waqf": {"en": "the Telangana Waqf Board", "te": "తెలంగాణ వక్ఫ్ బోర్డు", "ur": "تلنگانہ وقف بورڈ"},
}

# Notes the citizen sees on each step. {ref}, {place}, {date} and {department} are filled in.
NOTES = {
    "received": {
        "en": "We received your report. Your reference is {ref}.",
        "te": "మీరు పంపిన సమాచారం అందింది. మీ సూచిక సంఖ్య {ref}.",
        "ur": "آپ کی رپورٹ موصول ہو گئی۔ آپ کا حوالہ نمبر {ref} ہے۔",
    },
    "routed_area": {
        "en": "Officials of the area have been asked to check it against satellite images and records.",
        "te": "ఉపగ్రహ చిత్రాలు, రికార్డులతో దీన్ని పరిశీలించమని ఆ ప్రాంత అధికారులను కోరాం.",
        "ur": "علاقے کے افسران سے کہا گیا ہے کہ وہ اسے سیٹلائٹ تصاویر اور ریکارڈ سے جانچیں۔",
    },
    "linked_incident": {
        "en": "It matches a change officials are already reviewing at {place}.",
        "te": "{place} వద్ద అధికారులు ఇప్పటికే పరిశీలిస్తున్న మార్పుతో ఇది సరిపోలుతోంది.",
        "ur": "یہ {place} پر اس تبدیلی سے ملتی ہے جس کا افسران پہلے ہی جائزہ لے رہے ہیں۔",
    },
    "duplicate": {
        "en": "Others reported the same place. You will get the same updates.",
        "te": "ఇదే ప్రదేశం గురించి ఇతరులు కూడా తెలిపారు. మీకూ అవే సమాచారాలు అందుతాయి.",
        "ur": "اسی جگہ کی اطلاع دوسروں نے بھی دی ہے۔ آپ کو بھی وہی اطلاعات ملیں گی۔",
    },
    "not_watched": {
        "en": "This place is not on GeoGuard's watch list yet. Officials will add it, or pass your report to the right department.",
        "te": "ఈ ప్రదేశం ఇంకా GeoGuard పరిశీలన జాబితాలో లేదు. అధికారులు దీన్ని జాబితాలో చేరుస్తారు, లేదా మీ సమాచారాన్ని సంబంధిత శాఖకు పంపుతారు.",
        "ur": "یہ جگہ ابھی GeoGuard کی نگرانی کی فہرست میں نہیں ہے۔ افسران اسے فہرست میں شامل کریں گے یا آپ کی رپورٹ متعلقہ محکمے کو بھیجیں گے۔",
    },
    "no_place": {
        "en": "We need the exact place. Officials will try to find it from your description.",
        "te": "ఖచ్చితమైన ప్రదేశం కావాలి. మీ వివరణ ఆధారంగా అధికారులు దాన్ని గుర్తించే ప్రయత్నం చేస్తారు.",
        "ur": "ہمیں صحیح جگہ معلوم ہونی چاہیے۔ افسران آپ کی تفصیل سے اسے تلاش کرنے کی کوشش کریں گے۔",
    },
    "placed": {
        "en": "Officials found the place: {place}.",
        "te": "అధికారులు ప్రదేశాన్ని గుర్తించారు: {place}.",
        "ur": "افسران نے جگہ تلاش کر لی: {place}۔",
    },
    "change_found": {
        "en": "The satellite images show a change at this place. Officials are reviewing it.",
        "te": "ఉపగ్రహ చిత్రాల్లో ఈ ప్రదేశంలో మార్పు కనిపించింది. అధికారులు దాన్ని పరిశీలిస్తున్నారు.",
        "ur": "سیٹلائٹ تصاویر میں اس جگہ پر تبدیلی نظر آئی ہے۔ افسران اس کا جائزہ لے رہے ہیں۔",
    },
    "satellite_checked": {
        "en": "Satellite images up to {date} were checked: no change large enough to see from space yet. Small works may not show; officials will still look at your report.",
        "te": "{date} వరకు ఉపగ్రహ చిత్రాలను పరిశీలించాం: అంతరిక్షం నుండి కనిపించేంత పెద్ద మార్పు ఇంకా లేదు. చిన్న పనులు కనిపించకపోవచ్చు; అధికారులు మీ సమాచారాన్ని ఇంకా పరిశీలిస్తారు.",
        "ur": "{date} تک کی سیٹلائٹ تصاویر دیکھی گئیں: ابھی تک خلا سے نظر آنے جتنی بڑی تبدیلی نہیں ملی۔ چھوٹے کام شاید نظر نہ آئیں؛ افسران پھر بھی آپ کی رپورٹ دیکھیں گے۔",
    },
    "check_visible": {
        "en": "Officials checked the satellite images: a change is visible. They are reviewing it.",
        "te": "అధికారులు ఉపగ్రహ చిత్రాలను పరిశీలించారు: మార్పు కనిపిస్తోంది. వారు దాన్ని సమీక్షిస్తున్నారు.",
        "ur": "افسران نے سیٹلائٹ تصاویر دیکھیں: تبدیلی نظر آ رہی ہے۔ وہ اس کا جائزہ لے رہے ہیں۔",
    },
    "check_not_visible": {
        "en": "Officials checked the satellite images: no change is visible yet. Small works may not show from space.",
        "te": "అధికారులు ఉపగ్రహ చిత్రాలను పరిశీలించారు: ఇంకా మార్పు కనిపించలేదు. చిన్న పనులు అంతరిక్షం నుండి కనిపించకపోవచ్చు.",
        "ur": "افسران نے سیٹلائٹ تصاویر دیکھیں: ابھی کوئی تبدیلی نظر نہیں آئی۔ چھوٹے کام خلا سے شاید نظر نہ آئیں۔",
    },
    "added_to_watch": {
        "en": "This place is now on GeoGuard's weekly watch: {place}.",
        "te": "ఈ ప్రదేశం ఇప్పుడు GeoGuard వారపు పరిశీలనలో ఉంది: {place}.",
        "ur": "یہ جگہ اب GeoGuard کی ہفتہ وار نگرانی میں ہے: {place}۔",
    },
    # Closing reasons.
    "incident_confirmed": {
        "en": "Closed: officials confirmed a change at this place. Action is with the department.",
        "te": "ముగిసింది: ఈ ప్రదేశంలో మార్పును అధికారులు నిర్ధారించారు. చర్య సంబంధిత శాఖ వద్ద ఉంది.",
        "ur": "بند: افسران نے اس جگہ پر تبدیلی کی تصدیق کی ہے۔ کارروائی متعلقہ محکمے کے پاس ہے۔",
    },
    "incident_dismissed": {
        "en": "Closed: officials reviewed this place and found no change that needs action.",
        "te": "ముగిసింది: అధికారులు ఈ ప్రదేశాన్ని పరిశీలించారు; చర్య అవసరమైన మార్పు కనిపించలేదు.",
        "ur": "بند: افسران نے اس جگہ کا جائزہ لیا اور کوئی ایسی تبدیلی نہیں ملی جس پر کارروائی ضروری ہو۔",
    },
    "no_change_seen": {
        "en": "Closed: officials checked the satellite images and records and found no change that needs action. If the work continues, please report again with a new photo.",
        "te": "ముగిసింది: అధికారులు ఉపగ్రహ చిత్రాలు, రికార్డులను పరిశీలించారు; చర్య అవసరమైన మార్పు కనిపించలేదు. పని కొనసాగితే, కొత్త ఫోటోతో మళ్లీ తెలపండి.",
        "ur": "بند: افسران نے سیٹلائٹ تصاویر اور ریکارڈ دیکھے اور کوئی ایسی تبدیلی نہیں ملی جس پر کارروائی ضروری ہو۔ اگر کام جاری رہے تو نئی تصویر کے ساتھ دوبارہ اطلاع دیں۔",
    },
    "authorised": {
        "en": "Closed: the work at this place is covered by a recorded government work or permission.",
        "te": "ముగిసింది: ఈ ప్రదేశంలోని పనికి నమోదైన ప్రభుత్వ పని లేదా అనుమతి ఉంది.",
        "ur": "بند: اس جگہ کا کام ریکارڈ شدہ سرکاری کام یا اجازت کے تحت ہے۔",
    },
    "passed_on": {
        "en": "Closed here: this place is outside what GeoGuard watches. Your report was passed to {department}.",
        "te": "ఇక్కడ ముగిసింది: ఈ ప్రదేశం GeoGuard పరిశీలన పరిధిలో లేదు. మీ సమాచారాన్ని {department}కు పంపాం.",
        "ur": "یہاں بند: یہ جگہ GeoGuard کی نگرانی سے باہر ہے۔ آپ کی رپورٹ {department} کو بھیج دی گئی ہے۔",
    },
    "not_enough": {
        "en": "Closed: we could not place or understand this report. Please report again with a pin on the map and a photo.",
        "te": "ముగిసింది: ఈ సమాచారంలోని ప్రదేశాన్ని గానీ, విషయాన్ని గానీ గుర్తించలేకపోయాం. మ్యాప్‌పై గుర్తు, ఫోటోతో మళ్లీ తెలపండి.",
        "ur": "بند: ہم اس رپورٹ کی جگہ یا بات نہیں سمجھ سکے۔ نقشے پر نشان اور تصویر کے ساتھ دوبارہ اطلاع دیں۔",
    },
}
CLOSE_REASONS = ("incident_confirmed", "incident_dismissed", "no_change_seen", "authorised", "passed_on", "not_enough")

PLACE_UNWATCHED = {"en": "a place not on the watch list", "te": "పరిశీలన జాబితాలో లేని ప్రదేశం", "ur": "نگرانی کی فہرست سے باہر کی جگہ"}

# The WhatsApp conversation.
BOT = {
    "welcome": (
        "GeoGuard: Telangana's weekly watch over lakes and government land.\n"
        "Reply with a number / సంఖ్యతో జవాబివ్వండి / نمبر کے ساتھ جواب دیں:\n"
        "1 English\n2 తెలుగు\n3 اردو\n"
        "To check a report, send its reference, for example GGR-7K3M-9QXA."
    ),
    "ask_place": {
        "en": "Share the place: tap 📎, then Location, and send the pin. Or type the nearest landmark, village and mandal.",
        "te": "ప్రదేశాన్ని పంపండి: 📎 నొక్కి, Location ఎంచుకుని పిన్ పంపండి. లేదా దగ్గరలోని గుర్తు, గ్రామం, మండలం టైప్ చేయండి.",
        "ur": "جگہ بھیجیں: 📎 دبائیں، پھر Location چن کر پن بھیجیں۔ یا قریبی نشانی، گاؤں اور منڈل لکھیں۔",
    },
    "ask_what": {
        "en": "What is happening there? Reply with a number:",
        "te": "అక్కడ ఏమి జరుగుతోంది? సంఖ్యతో జవాబివ్వండి:",
        "ur": "وہاں کیا ہو رہا ہے؟ نمبر کے ساتھ جواب دیں:",
    },
    "ask_photo": {
        "en": "Send a photo of it, or reply SKIP.",
        "te": "దాని ఫోటో పంపండి, లేదా SKIP అని పంపండి.",
        "ur": "اس کی تصویر بھیجیں، یا SKIP لکھیں۔",
    },
    "ask_describe": {
        "en": "Describe it in a few words, or reply SKIP. Please do not name any person.",
        "te": "కొన్ని మాటల్లో వివరించండి, లేదా SKIP అని పంపండి. దయచేసి ఎవరి పేరూ రాయకండి.",
        "ur": "چند الفاظ میں بیان کریں، یا SKIP لکھیں۔ براہ کرم کسی شخص کا نام نہ لکھیں۔",
    },
    "ask_updates": {
        "en": "Do you want updates on this WhatsApp number? Reply YES or NO.",
        "te": "ఈ WhatsApp నంబర్‌కు సమాచారం కావాలా? YES లేదా NO అని పంపండి.",
        "ur": "کیا آپ اس واٹس ایپ نمبر پر اطلاعات چاہتے ہیں؟ YES یا NO لکھیں۔",
    },
    "done": {
        "en": "Thank you. {first}\nSend {ref} at any time to see its status.",
        "te": "ధన్యవాదాలు. {first}\nస్థితి తెలుసుకోవడానికి ఎప్పుడైనా {ref} పంపండి.",
        "ur": "شکریہ۔ {first}\nحالت جاننے کے لیے کسی بھی وقت {ref} بھیجیں۔",
    },
    "status": {"en": "Report {ref}: {status}.\n{note}", "te": "సమాచారం {ref}: {status}.\n{note}", "ur": "رپورٹ {ref}: {status}۔\n{note}"},
    "not_found": {
        "en": "No report has that reference. Check it and send it again.",
        "te": "ఆ సూచిక సంఖ్యతో సమాచారం లేదు. సరిచూసి మళ్లీ పంపండి.",
        "ur": "اس حوالہ نمبر کی کوئی رپورٹ نہیں ملی۔ جانچ کر دوبارہ بھیجیں۔",
    },
    "invalid": {"en": "Sorry, I did not understand.", "te": "క్షమించండి, అర్థం కాలేదు.", "ur": "معذرت، سمجھ نہیں آیا۔"},
    "outside": {
        "en": "That pin is outside Telangana. Please send the place again.",
        "te": "ఆ పిన్ తెలంగాణ బయట ఉంది. దయచేసి ప్రదేశాన్ని మళ్లీ పంపండి.",
        "ur": "یہ پن تلنگانہ سے باہر ہے۔ براہ کرم جگہ دوبارہ بھیجیں۔",
    },
    "photo_kept": {"en": "Photo received.", "te": "ఫోటో అందింది.", "ur": "تصویر موصول ہو گئی۔"},
    "photo_not_fetched": {
        "en": "Photo noted. It could not be downloaded yet; officials will see that you sent one.",
        "te": "ఫోటో నమోదైంది. ఇంకా డౌన్‌లోడ్ కాలేదు; మీరు ఫోటో పంపినట్లు అధికారులకు తెలుస్తుంది.",
        "ur": "تصویر نوٹ کر لی گئی۔ ابھی ڈاؤن لوڈ نہیں ہو سکی؛ افسران کو معلوم ہوگا کہ آپ نے تصویر بھیجی ہے۔",
    },
    "too_many": {
        "en": "You have sent many reports today. Please try again tomorrow.",
        "te": "ఈ రోజు మీరు చాలా సమాచారాలు పంపారు. దయచేసి రేపు మళ్లీ ప్రయత్నించండి.",
        "ur": "آپ آج بہت سی رپورٹیں بھیج چکے ہیں۔ براہ کرم کل دوبارہ کوشش کریں۔",
    },
    "restart": {"en": "Send RESTART to start again.", "te": "మళ్లీ మొదలుపెట్టడానికి RESTART పంపండి.", "ur": "دوبارہ شروع کرنے کے لیے RESTART بھیجیں۔"},
}
SKIP = {"skip", "వద్దు", "چھوڑیں", "no photo"}
YES = {"yes", "y", "1", "అవును", "ہاں", "haan", "ha"}
NO = {"no", "n", "2", "కాదు", "వద్దు", "نہیں", "nahi"}
WHAT_ORDER = ("dumping", "construction", "fencing", "clearing", "other")


def pick(table: dict, language: str) -> str:
    return table.get(language) or table["en"]


def note(key: str, **values) -> dict:
    """A public note in all three languages."""
    out = {}
    for lang in LANGS:
        v = {k: (pick(x, lang) if isinstance(x, dict) else x) for k, x in values.items()}
        out[lang] = NOTES[key][lang].format(**v)
    return out
