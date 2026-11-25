# Citizen channels: reports in, updates out (M15)

Built 25 November 2026 (DECISIONS.md D-062), to CONTEXT.md section 17.8. A citizen tells GeoGuard
about a problem on public land, and hears back at each step.

## 1. The flow

```
UPSTREAM (in)                                   GEOGUARD                                  DOWNSTREAM (out)
web portal /report  ─┐                                                                ┌─ status page /report/track/<ref>
WhatsApp chatbot    ─┼─►  reference number at once                                   ├─ SMS at each step (verified phone)
1070 helpline       ─┤    placed on a watched location: inside, buffer, watch ring   ├─ WhatsApp at each step (the chat's number)
Praja Vani petition ─┤    merged with a report of the same place (100 m, 60 days)    │
visit in person     ─┘    linked to an incident within 150 m                         │   in English, Telugu or Urdu
                          signal (CONTEXT.md section 7)                              │   never: officer names, owner names,
                          area's officials and the admin notified (D-059)  ──────────┘   evidence, or "illegal"
```

A report never makes a finding on its own (CONTEXT.md section 5). It asks officials to look. The
satellite screen and the records do the rest.

## 2. Upstream: how reports come in

| Channel | Who uses it | In this build |
|---|---|---|
| **Web portal**, `/report` | Anyone, with no sign-in | Built. A map pin or "use my location", what is happening (five choices), up to 3 photos, a few words, and optionally a verified phone for updates. English, Telugu and Urdu; Urdu reads right to left |
| **WhatsApp** | Anyone with WhatsApp | Built as a conversation (one question at a time, by number, in the three languages). **Real messages need the State's WhatsApp Business agreement**: HYDRAA's number or MeeSeva on WhatsApp. Until then the webhook refuses messages (`503`), and the desk's **WhatsApp (demo)** page runs the same conversation from a fictional number |
| **1070 helpline, Praja Vani, visits** | Staff at the desk | Built. **Citizen reports → Enter a call or petition**: the call or petition number, the caller's language, the place on the map or in words, what they said. Staff read the reference back |

**On arrival, every report:**
1. Gets a reference like `GGR-7K3M-9QXA`. It is random, so references cannot be guessed in order.
2. Is placed:
   - inside, in the buffer or in the watch ring of a watched location;
   - outside them all ("not on the watch list");
   - or with no pin ("needs the place").
3. Is merged with an open report within 100 m from the last 60 days. The later one follows the
   earlier: it shares every update and tells no one again.
4. Is linked to an open, under-review or confirmed incident within 150 m on the same location.
5. Becomes a row in `signals` (kind `citizen_report`).
6. Is notified to the area's officials (routing by area, D-059) and every admin.
   - **Needs acknowledgement** when it is not already on an incident.
   - **Follow-up:** a reminder after 24 hours, and the admin is told after 48.
   - **Acknowledging:** recording a check or closing the report counts as acknowledging it.
   - **Outside the inbox:** email only, because the SMS and WhatsApp templates are worded for
     incidents.

**Checks:**
- **Place:** the pin must lie in Telangana, or in the demo world for demo reports.
- **Photos:** JPEG, PNG or WebP, at most 8 MB, re-encoded at most 2048 px a side. Re-encoding drops
  EXIF: camera, time and the phone's own location.
- **Rate limits:**
  - **Reports:** 5 an hour and 20 a day from one source.
  - **Codes:** 3 a phone an hour, and 5 tries a code.
  - **Status lookups:** 30 a minute.
  - **Source:** a salted hash of the network address or phone; the address itself is never stored.
- **Repeated false reports:** when the admin marks two reports from one source as false, that
  source's later reports carry a flag for officials. They are not blocked.

## 3. On the desk: what officials do

**Where:** **Citizen reports** in the side bar. A map and a list, filtered open, all or closed.
Each report shows:
- the place and zone;
- the linked incident and any duplicates;
- the photos and the citizen's words;
- the history (what the citizen read, and the note for the record);
- the messages sent to the citizen.

**Officials never see a citizen's number or name.** They see only whether updates go to a verified
phone (masked, for example `+91******0003`).

| Step | Who | What the citizen reads |
|---|---|---|
| Record a check: a change is visible | Official or admin | "Officials checked the satellite images: a change is visible. They are reviewing it." |
| Record a check: nothing visible yet | Official or admin | "...no change is visible yet. Small works may not show from space." |
| Place it on a location or incident | Admin | "Officials found the place: ..." or, for a location just added from it, "This place is now on GeoGuard's weekly watch" |
| Close: no change that needs action | Admin | "...If the work continues, please report again with a new photo." |
| Close: covered by a recorded work or permission | Admin | "...covered by a recorded government work or permission." |
| Close: passed to a department | Admin | "...passed to the Revenue Department (Tahsildar)", or the municipality, Irrigation, HYDRAA, Forest, Endowments or the Waqf Board |
| Close: could not place or understand it | Admin | "...Please report again with a pin on the map and a photo." |

**Steps the system takes on its own:**
- **An incident opens on the place:** "The satellite images show a change at this place."
- **The admin confirms the incident:** the report closes with "officials confirmed a change. Action
  is with the department."
- **The admin dismisses the incident:** the report closes with "found no change that needs action."
- **The weekly screen** sees the place clearly with no change: "Satellite images up to <date> were
  checked: no change large enough to see from space yet. Small works may not show." The report
  stays open for an official.

The incident page lists the citizen reports of its place, by reference.

## 4. Downstream: how citizens hear back

| Channel | In this build | To switch it on |
|---|---|---|
| **Status page** `/report/track/<ref>` | Always. Status and every public note, in English, Telugu or Urdu | Nothing |
| **SMS** | A message at each step to a phone verified by one-time password. Every message is **held** | The State's SMS gateway agreement, and two DLT templates (`citizen_update`, `citizen_otp` in `api/app/notify/channels.yaml`). Until then, the portal says SMS updates are not available yet and does not ask for a number |
| **WhatsApp** | Replies inside the conversation. Later updates need the approved template `citizen_update`. Every message is **held** | The WhatsApp agreement, `LP_WHATSAPP_APP_SECRET`, `LP_WHATSAPP_VERIFY_TOKEN` and `LP_WHATSAPP_TOKEN` in `.env`, and the template approved |

**How messages are sent:**
- **SMS:** carries the reference, the status and the link, because DLT fixes the words. The full
  note is on the status page.
- **Held messages:** a held message is never sent later.
- **Demo:** demo messages never leave the machine. The demo shows the one-time code on screen.
- **Retries:** a failed attempt is retried after 5 minutes, up to three attempts.
- **Record:** every attempt is an append-only row with a masked number.

## 5. Privacy (DPDP Act 2023) and safety

- **Name and phone:**
  - Optional, and kept only to send updates, once the citizen has proved the phone is theirs: a
    one-time password, the WhatsApp number itself, or staff taking it from the caller.
  - The citizen agrees to that use on the form.
  - Both are removed 90 days after the report closes (the notifier does it). The report and its
    history stay.
- **WhatsApp chat state:** the number in it is removed after 24 hours without a message.
- **The audit log** records each step with the reference, never the citizen's words, name or
  number.
- **Accused persons are never shown in public.** The portal and the status page show no owner,
  claimant or officer, no photo and no evidence. Citizens are asked not to name anyone.
- **The history is append-only.** The database refuses any change to `citizen_report_events` and
  `citizen_messages`.

## 6. Files

| Part | File |
|---|---|
| Tables, notification kind, guards | `api/migrations/versions/0009_citizen.py` |
| Intake, placing, merging, events, automatic steps, retention | `api/app/citizen/service.py` |
| Words in English, Telugu and Urdu | `api/app/citizen/texts.py` |
| One-time passwords | `api/app/citizen/otp.py` |
| WhatsApp conversation and webhook parsing | `api/app/citizen/whatsapp.py` |
| SMS and WhatsApp messages to citizens | `api/app/citizen/sender.py`, `api/app/notify/channels.yaml` |
| Public API | `api/app/routers/citizen.py` |
| Desk API | `api/app/routers/reports.py` |
| Hooks | `services/ingest.py` (incident opened), `workflow/incidents.py` (decided), `routers/pipeline.py` (weekly screen), `notify/service.py` (notifications, the notifier) |
| Portal | `web/src/portal/Portal.tsx`, `portal.css`, `web/src/i18n/ur.json` |
| Desk | `web/src/desk/Reports.tsx` (list, report, intake, WhatsApp demo); the panel on the incident page |
| Demo reports | `data/demo/world.yml` (`citizen_reports`), `api/app/seed/demo.py` |
| Tests | `api/tests/test_citizen.py` (13), `api/tests/test_demo_seed.py`, `e2e/tests/m15-citizen.spec.ts` |

**API.**
- **Public:**
  - `GET /citizen/config`;
  - `POST /citizen/reports`, `GET /citizen/reports/{ref}`;
  - `POST /citizen/otp`, `/citizen/otp/verify`;
  - `GET|POST /citizen/whatsapp/webhook`.
- **Desk:**
  - `GET /reports`, `POST /reports/intake`, `GET /reports/{id}`, `GET /reports/{id}/photos/{n}`;
  - `POST /reports/{id}/check`;
  - `/close` and `/link` (admin);
  - `GET|POST /reports/whatsapp-simulator`.

## 7. Not built yet

- **Downloading WhatsApp photos.** It needs the provider's media token. Until then the report notes
  that a photo was sent.
- **Voice notes and long messages on WhatsApp.**
- **A public map or figures by district.** The portal shows only 30-day totals, so no place is ever
  named in public.
- **Overview figures for citizen reports.**
- **Delivery receipts from the gateways.**
- **Urdu on the desk.** Officials work in English and Telugu.
- **Native-speaker review.** The Telugu and Urdu wording is a draft.
