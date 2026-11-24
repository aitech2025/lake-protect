# Lake Protect: the jury's hardest questions

Short, honest answers for the Q&A. If an answer isn't known, offer to come back with it; never guess. The appendix slides in the deck are noted where they help.

## Does it work?

**How accurate is it?**
We don't know yet, and we won't claim a number until we do. The blind backtest on 30 public cases runs in December 2026. It passes if at least 21 of the 30 are flagged before public action, and we stop if fewer than 15 are. The pilot target is 70% field-confirmed precision by month 6. That is a target to agree with HYDRAA, not a result.

**What about the 58 candidate changes found on real lakes?**
They are candidates, not findings. Every one stays on the watch list, because the lake outlines come from OpenStreetMap and are not notified boundaries. Some are at lakes where HYDRAA reported restoration works in 2026. That is exactly why the legal check looks for authorised works.

**How does it see during the monsoon?**
Cloud cover over Hyderabad averages 79–89% from June to September. Sentinel-1 radar sees through cloud. Radar already confirms buildings: the return must rise by 3 dB or more, and it refused 25 building candidates in the real screen. Radar-only alerts in the monsoon are designed but not built yet. They will be marked "optical confirmation pending".

**Can it see a shed or a compound wall?**
Not from 10 m imagery, and we don't claim to. Small structures need sub-metre images (Cartosat-3 through NRSC, or commercial imagery at 0.3–0.5 m) or a field visit. This is why there are three tiers: screen, confirm, verify.

**Lakes shrink every summer. Won't that flood officers with alerts?**
No. Water loss alone never raises an alert. Before anything becomes a candidate, the season, drought, persistence and minimum-area controls all apply. In the real screen they cut 124,203 changed pixels down to 58 candidate changes.

## Law and evidence

**Who decides whether a change is illegal?**
An officer, always. The system reports physical change with dates. It never labels anything illegal and never recommends demolition, and an automated test checks every English and Telugu string in the product.

**Will the evidence hold up in court?**
Each pack holds:
- a dated image pair;
- the rule and software versions;
- the boundary version;
- the field record with hashed, geotagged photos;
- a SHA-256 manifest of every file;
- a draft Section 63(4) certificate under the Bharatiya Sakshya Adhiniyam.

`lp verify-pack` shows whether a single byte has changed. The certificate wording still needs counsel's review.

**Only 23% of HMDA lakes have a final FTL notice. What about the rest?**
Boundary status decides what an alert may do (appendix A2):
- final or physically marked boundaries get the full officer path;
- derived outlines get a field check only;
- land known only by survey number stays watch-only.

A live court matter puts any alert on legal hold.

**Could alerts be used to target or extort people?**
Detection and the priority score are owner-blind. Owner names appear only after field confirmation, and only to nodal, revenue and legal roles. Every view is logged. Downloads are single-case.

## The State's fit

**HYDRAA already has NRSC data, HYDRAA-Raksha and CCTV. Why this?**
Those tools show the lakes; this closes the loop. It takes each change through a legal check, a named officer with a deadline, a field visit and a sealed case file. It is not another map viewer.

**What is actually built today?**
See appendix A3. Built:
- detection on 99 real lakes;
- the legal check;
- the state machine with escalation;
- the offline field app;
- evidence packs;
- the hash-chained audit.

Designed, not built: State single sign-on, row-level security, S3 storage with object lock, the outbox, and citizen intake by WhatsApp and the web. Proposal slide 26 overstates this; answer from A3.

**Where does the data live, and what about the DPDP Act?**
In the State Data Centre or an approved Indian cloud, and the State owns all data. Citizen reporter details are kept to a minimum. The DPDP Rules' main duties apply from May 2027, during the paid pilot, and the design already follows them.

**What does it cost?**
- Backtest and demonstration: no cost.
- Paid pilot (100 lakes and 10 parcels): ₹40–60 lakh.
- Core urban region: ₹4.5–9.5 crore a year.

These are indicative planning estimates, not quotes. One year of watch for the core urban region costs less than one acre at HYDRAA's Ailapur estimate of ₹17.4 crore.

**What does the State have to give?**
A named officer, the official FTL boundary files, and the register of authorised works. Without official boundary access by March 2027, we stop.

**Is the State locked in to you or to one imagery provider?**
No. The stack is open source (FastAPI, PostgreSQL and PostGIS, React) and runs in Docker on State hardware. Each imagery tier can use free, ISRO or commercial images, chosen per phase.

## Open items to settle before the jury

- **One product name.** The architecture pages say "Telangana GeoGuard"; the proposal and this deck say "Lake Protect".
- **Proposal slide 26.** Change it to match appendix A3.
