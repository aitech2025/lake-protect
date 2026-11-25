# Citizen channels: a report opens an incident, and the citizen hears back (M15, M16, M17)

Built 25 November 2026 to CONTEXT.md section 17.8 (DECISIONS.md D-062). Changed the same day at
the owner's request (D-063):
- Urdu is removed. The channel works in English and Telugu.
- Every report now goes into the regular incident flow:
  1. the app finds the place;
  2. it reviews the place with satellite imagery;
  3. it tells the officials;
  4. the officials work the report as an incident, with reviews, a sharper image, a decision and
     closing, each with a note.

The owner then asked (D-064) that officials and the admin alike can acknowledge it, add notes,
compare satellite looks of the place by date, attach the legal records, approve or decline, and
put the place on the weekly watch. See section 5a.

## 1. The flow

```
IN                         GEOGUARD                                                        OUT (to the citizen)
web portal /report  ─┐     reference at once                                               status page /report/track/<ref>
WhatsApp chatbot    ─┤     1. place: the pin, or words naming a watched location           SMS (verified phone)
1070 helpline       ─┼──►  2. district, mandal, survey numbers; zone of the location  ──►  WhatsApp (the chat's number)
Praja Vani petition ─┤     3. incident: same place reported → follows it                   English or Telugu, at each step:
visit in person     ─┘        open incident within 150 m → joins it                        case opened, satellite result,
                              otherwise → a new citizen incident                           under review, sharper images asked,
                           4. satellite review of the place (demo: at once; real: the        confirmed / dismissed / passed on
                              screener, within minutes)
                           5. officials notified (area routing, D-059), with the result
                           6. regular flow: review → sharper imagery → decide → close
```

A report never makes a finding on its own (CONTEXT.md section 5). It opens a case that an official
must look at. The satellite review and the officials' notes do the rest.

## 2. Finding the place (`api/app/citizen/locate.py`)

| What the citizen gave | What the app does |
|---|---|
| A pin (map, "use my location", or WhatsApp location) | Takes the watched location and zone that hold it. If none does, it makes a **reported place**: a 50 m circle, kind "Places reported by citizens", not on the weekly watch |
| Words only (a WhatsApp landmark, a caller's description) | If the words name exactly one watched location ("near the bund of Kapra lake"), places the report on it and flags "placed from the words, check the place". Otherwise the admin is asked to put it on the map, on the report's page |

**Area and land records at the pin:**
- **District and mandal** come from the matched location.
- **Outside every location**, they come from OpenStreetMap's boundaries (`data/areas/admin_orr.geojson`,
  made by `lp assets-areas`). The incident says these are not the revenue record.
- **Survey numbers** at the pin are shown when land records are loaded (M11).

The district decides which officials are told.

## 3. The incident

**A new citizen incident (origin `citizen`):**
- **The location:** the matched location, or the reported place.
- **The outline:** the reported spot, a 30 m circle around the pin. The change type follows what
  the citizen chose: soil dumped becomes land fill, construction becomes construction, a fence or
  wall becomes a small structure, and clearing becomes clearing.
- **The legal check runs and is kept**, but it never closes a citizen incident on its own: an
  official always looks.
- **The incident list** marks it **Citizen report**.
- **The incident page** shows:
  - the citizen's words and photos;
  - how the place was found;
  - the area source and survey numbers;
  - the satellite review.

**A report next to an open incident** (within 150 m) joins it instead, and the incident page lists
it. **A report of a place already reported** (100 m, 60 days) follows the earlier report.

## 4. The satellite review

| Data | Who looks | When |
|---|---|---|
| Demo world | The demo sensor, in the API | At once, before officials are told. A change the weekly screen has not seen yet (`unscreened_changes` in `data/demo/world.yml`, at Demo Kunta 7) is found; elsewhere it shows no change |
| Real | `lp review-reports`, which screens the location now with the weekly screen's rules and imagery (Sentinel-2, and Sentinel-1 radar for built-up). It runs as the `reviewer` service, every 5 minutes, and needs internet: `docker compose --profile screen up -d reviewer` | Within minutes. Officials are told when the incident opens, and again with the result |

**The results:**
- **A change is visible:** the nearest change within 150 m of the pin, with its area, date and
  before and after images.
- **No change visible yet:** the latest clear image.
- **No clear image yet:** too much cloud.
- **Failed:** after three failed tries.

The images and scenes become the incident's images and observations, so the evidence pack carries
them.

**Small works may not show:** Sentinel-2 has 10 m pixels, and the smallest change it reports is
1,000 sq m. The citizen is told so, and officials are prompted to ask for a sharper image.

## 5. The regular flow, and what the citizen reads

| Officials' step (incident page) | Citizen reads |
|---|---|
| (opened) | "Officials have opened a case for this place. The app is checking it against satellite images." |
| (satellite review) | "The newest satellite images show a change at this place, first seen …", or "… show no change large enough to see from space. Small works may not show …", or "no clear image yet, because of cloud" |
| A review (the incident moves to under review) | "An official is reviewing it." |
| Request sharper imagery | "Officials have asked for sharper satellite images of this place." |
| Confirm, with a note | "Closed: officials confirmed a change at this place. Action is with the department." |
| Dismiss, with a note | "Closed: officials reviewed this place and found no change that needs action. If the work continues, please report again with a new photo." |
| Dismiss, choosing **Passed to a department** | "Closed here: … Your report was passed to the Revenue Department (Tahsildar)", or the municipality, Irrigation, HYDRAA, Forest, Endowments or the Waqf Board |
| Close, with a note | (no new note: the citizen already has the outcome) |

**What stays inside, and false reports:**
- Officials' notes stay inside. Citizens read only these fixed notes.
- When declining, an official or the admin can also mark the report as false. Two false reports
  from one source flag its later reports for officials. They are not blocked.

## 5a. What officials and the admin do on a citizen's incident (M17, D-064)

The incident page shows one panel for citizen incidents (`web/src/desk/CitizenActions.tsx`). Both
roles can use all of it.

| Step | What happens | Citizen reads |
|---|---|---|
| **Acknowledge** (optional note) | Once per person. Clears that person's notifications for the incident. The first one starts the review. | "An official is reviewing it." |
| **Add a note** | Kept for good, shown with author and time. | Nothing: notes stay inside. |
| **Satellite look**, latest or on a date | **Demo:** answered at once. **Real:** `lp review-reports` answers it as of that date. The incident's own images are never replaced. Tick two looks to compare them side by side. | Nothing |
| **Sharper image** | **Official's request:** waits for the admin's approval or decline, with a note. **Admin's request:** approved as made. Nothing is ordered in the prototype. | "Officials have asked for sharper satellite images of this place." |
| **Attach the legal records** | A dated snapshot, kept beside the earlier ones: land records at the spot, boundary, documents, court cases, permits, authorised works, the legal check, and the sources still to check by hand. | Nothing |
| **Attach a legal document** | A file or a reference. It is kept on the location too. | Nothing |
| **Approve** or **Decline**, with a note | Starts the review if it is still open. Decline can pass the report to a department or mark it false. The admin is told of an official's decision. | As in section 5 |
| **Close**, with a note | After approving or declining. | Nothing new |
| **Add to the weekly watch** (reason, optional name) | For a reported place that is not watched yet. Every screen from then on looks at it. | "This place is now on GeoGuard's weekly watch: …" |

API: `POST /alerts/{id}/acknowledge`, `/notes`, `/satellite-looks`, `/imagery-request`,
`/imagery-requests/{rid}/decision` (admin), `/legal-records`, `/documents`, `/decision`, `/watch`.
Look images: `GET /alerts/{id}/looks/{review_id}/{before|after}`.

## 6. How citizens hear back

| Channel | In this build | To switch it on |
|---|---|---|
| **Status page** `/report/track/<ref>` | Always, in English or Telugu | Nothing |
| **SMS** | An update at each step to a phone verified by one-time password. Every message is **held** | The State's SMS gateway agreement, and the DLT templates `citizen_update` and `citizen_otp` (`api/app/notify/channels.yaml`). Until then, the portal says SMS updates are not available yet |
| **WhatsApp** | Replies in the conversation; later updates through the template `citizen_update`. Every message is **held** | The WhatsApp agreement, the app secret, the verify token, the API token, and the approved template |

Demo messages never leave the machine. A held message is never sent later.

## 7. Privacy (DPDP Act 2023)

- **Name and phone:** optional, kept only for updates once verified, and removed 90 days after
  closing.
- **Officials see** a masked number only.
- **Photos** lose their EXIF.
- **The audit log** holds no citizen's words, name or number.
- **Nobody accused** is ever shown in public.
- **The report's history and messages** are append-only.

## 8. Files

| Part | File |
|---|---|
| Tables: reports, events, messages, codes, chats | `api/migrations/versions/0009_citizen.py` |
| Citizen incidents: origin and report on incidents, reported places, satellite reviews; no Urdu | `api/migrations/versions/0010_citizen_incidents.py` |
| Finding the place | `api/app/citizen/locate.py`, `data/areas/admin_orr.geojson` |
| Opening the incident, the satellite review, the demo sensor | `api/app/citizen/incident.py` |
| Intake, placing, events, steps passed on | `api/app/citizen/service.py` |
| Words (English, Telugu) | `api/app/citizen/texts.py` |
| Real reviews | `pipeline/lake_protect/review.py`, `lp review-reports`, the `reviewer` service; `GET`/`POST /pipeline/reviews` |
| Sharper imagery (official's request, admin's approval) | `api/app/services/imagery.py` |
| Officials' actions: acknowledge, notes, legal records, documents, decisions, weekly watch | `api/app/citizen/actions.py`, `api/migrations/versions/0011_incident_actions.py` |
| Desk | `web/src/desk/CitizenActions.tsx` (the officials' panel), `web/src/desk/AlertDetail.tsx` (citizen and satellite review panels), `Queue.tsx` (badge), `Reports.tsx` (log, intake, place on the map, WhatsApp demo) |
| Portal | `web/src/portal/Portal.tsx` |
| Tests | `api/tests/test_citizen.py` (14), `api/tests/test_incident_actions.py` (7), `pipeline/tests/test_review.py` (4), `e2e/tests/m15-citizen.spec.ts` (2) |

## 9. Not built yet

- **WhatsApp photo download.** It needs the provider's media token.
- **Geocoding of free text** beyond the names of watched locations.
- **A public map or district figures.**
- **Delivery receipts.**
- **Native-speaker review.** The Telugu wording is a draft.
