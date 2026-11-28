# Weekly processing, incidents and legal documents (M12)

Built 24 November 2026, at the owner's request. Assume the government records are loaded as the system of record (`docs/asset-load.md`, `docs/asset-engine.md`). Then every week:
1. Every asset is screened from satellite images.
2. Each asset's week is recorded, whether it changed or not.
3. A change is named plainly and opens an incident for the officials to review.

Every asset carries its legal documents. Only two roles remain (DECISIONS.md D-057).

## 1. The weekly run

```
watch list ──► Sentinel-2 looks (and radar for built-up) ──► rules (detect-v2) ──► changes
     │                                                                                   │
     │                                                                         POST /candidates (each change)
     │                                                                                   │
     │                                                    legal check ──► incident opened, closed at once, or the open one continued
     ▼
POST /pipeline/runs: one row per asset per week, with that week's image and the changes, each linked to its incident
```

- **Where it runs.** `lp screen` runs weekly: in the scheduled container (`docker compose --profile screen up -d screener`, every 168 hours) or by hand.
- **What it uses.** It reads the watch list from the API, then the clearest Sentinel-2 looks since each asset's baseline.
- **What it sends for every asset, changed or not:**
  - the week, for example `2026-W48`;
  - the status:

    | Status | Shown as |
    |---|---|
    | `no_candidate` | No change seen |
    | `candidate_found` | Change found |
    | `no_usable_look` | No clear look this week |
    | `not_observed` | Not observed |
    | `failed` | Screen failed |

  - **the week's image:** the latest clear look in true colour, with the boundary in blue, the buffer dashed red and any change found that week outlined yellow;
  - the changes, each with the incident ingest gave it.
- **No clear look is never "no change".** The record says "no change seen" only when there was a clear look.
- **Older reports.** `lp replay` resends a saved screen with its images. A report saved before M12 has no images; the API then finds its changes by time.
- **Image retention.** The most recent 60 days of per-asset weekly images use the active `weeks/` namespace and `lp_storage` volume. Older images use `archive/weeks/` and the separate durable `lp_archive` volume; their recorded object keys keep the history links working. This is a separate local archive volume, not a remote cold-storage tier.

**What changed, in the words officials use.**

| Change type | Shown as | How the rules see it (detect-v2) |
|---|---|---|
| `building` | Construction | Vegetation or bare ground becomes built-up, confirmed by radar (VV at least 3 dB higher) |
| `soil_fill` | Land fill | Water becomes bare soil or built-up, starting at the shore |
| `levelling` | Levelling | Ground with no dense vegetation (scrub, grass, mixed cover) becomes bare earth. New in detect-v2 |
| `clearing` | Clearing | Dense vegetation becomes bare soil |

Each incident carries one sentence built from these labels, for example "Land fill of about 4,474 sq m inside the boundary, first seen 10 Nov 2026".

Water loss alone never opens an incident: season and drought shrink lakes too.

## 2. Incidents

```
OPEN ──(an official's review, or the admin starts one)──► UNDER_REVIEW
UNDER_REVIEW ──(admin, with a note)──► CONFIRMED  or  DISMISSED
CONFIRMED / DISMISSED ──(admin, with a note)──► CLOSED
OPEN ──(system: the legal check)──► CLOSED, resolution "auto"
```

**Reviews.**
- **Who reviews.** Viewers (the officials) record reviews: a real change, not a real change, or needs a site visit, always with a note.
- **Effect.** The first review moves the incident to under review. More reviews add to it.
- **Storage.** Reviews are append-only rows.

**Decisions.**
- **Who decides.** The admin confirms or dismisses, then closes, each step with a note.
- **Evidence pack.** The admin makes an evidence pack for a confirmed change. It is sealed by SHA-256 and holds the image pair, the boundary, the legal check, the reviews, the decisions and the asset's documents.

**Closed at once by the legal check, with the reason shown:**
- a change outside the boundary, buffer and watch ring;
- a change first seen on or before the baseline date;
- a change matching authorised works or a permit outside the lake and buffer.

**Kept open and flagged:**
- a live court case;
- an unconfirmed boundary;
- a permit inside the lake or buffer.

The flagged facts are for the officials and the admin to weigh.

**The same change seen again.**
- While its incident is open, it is recorded on that incident ("seen again"), and no new incident opens.
- After the incident was closed or dismissed, a new incident opens and links back to the old one.

**Guards in the database:**
- A new incident must start open.
- A state changes only through `app/workflow/incidents.py`.
- The resolution must match the state.
- Reviews and the audit log are append-only.

## 3. Legal documents

Every asset carries its legal documents. Each document is a file (PDF, PNG or JPEG) with its SHA-256, or a reference held elsewhere, or both.

| Type | Examples |
|---|---|
| `notification` | Final or preliminary FTL notification |
| `survey_map` | Village map, FTL survey sheet, derived outline |
| `land_record` | Record of Rights extract, Sethwar, Khasra Pahani (no owner names) |
| `government_order` | G.O. on buffer widths |
| `court_order` | A case number, a stay or an order |
| `recovery_order` | HYDRAA's order recovering and marking land |
| `other` | Anything else |

**How documents are added:**
- **The admin** uploads a file or records a reference. The upload is refused if the file is not what it claims to be.
- **The source engine** tags each asset with the file its record came from:
  - the notification;
  - the recovery order;
  - the outline;
  - the village map and Record of Rights extract.
- **The demo seed** gives every demo asset fictional one-page PDFs.

**Corrections.** Rows are append-only. A correction is a new document that supersedes the old one; both stay visible.

**Reading.** Everyone can read and open documents, and every file opened is logged.

## 4. Roles

Superseded by D-067 (four personas, 28 Nov 2026):

| Persona | Sees | Can |
|---|---|---|
| `admin` | Everything | Maintain the application: people and areas, sources, documents, boundaries, records, satellites; override a priority. No step on an incident |
| `senior_official` | The whole State, including records, the monthly page and the audit log | Review; assign field visits; approve or return a recommendation; close; approve sharper images; make evidence packs. Decide directly where no district officer covers the place |
| `district_officer` | Their districts (or mandals) only | Review; assign, reassign or withdraw a field visit; return a field report; recommend confirm or dismiss; make evidence packs |
| `field_officer` | The incidents ever assigned to them, and their locations | Submit the field report (findings, GPS, up to five photos); add notes and documents while on the visit |

Lifecycle: OPEN, UNDER_REVIEW, FIELD_VISIT, FIELD_REPORTED, RECOMMENDED, CONFIRMED or DISMISSED, CLOSED.
The field visit is optional. See DECISIONS.md D-067 for who takes each step.

**What was retired:**
- the field app;
- field assignment;
- two-person closures;
- the escalation timers and their worker;
- the officer record;
- the case-readiness checklist.

Their code is in git history.

## 5. API

| Endpoint | Who |
|---|---|
| `GET /assets/{id}/weeks`, `GET /assets/{id}/weeks/{screen_id}/image` | Both |
| `GET /alerts`, `GET /alerts/{id}` (incidents, with `change_label` and `summary`) | Both |
| `POST /alerts/{id}/reviews` `{outcome, note}` | Viewer |
| `POST /alerts/{id}/transitions` `{to, note}` | Admin |
| `POST /alerts/{id}/evidence-pack` | Admin, confirmed changes only |
| `GET /assets/{id}/documents`, `GET /documents/{id}/file` | Both |
| `POST /assets/{id}/documents` (form: doc_type, title, reference, issued_on, file) | Admin |
| `GET /screening/runs?dataset=real\|demo` | Both |

## 6. Not yet done

- **Levelling (detect-v2)** has not been tuned on the tuning lakes. The scored backtest (M3) must judge it on real data before any accuracy is claimed (D-058).
- **The real lakes' weekly history** starts with the first screen after M12. Earlier weeks are not back-filled.
- **The pitch deck** still describes the field app, the officer path and two-person closures. Update it if the jury story should match.
