---
marp: true
theme: pitch-deck
paginate: true
header: "Lake Protect"
footer: "Lake Protect · TISC 2026 · Confidential"
---

<!-- _class: dark hero -->
<!-- _paginate: false -->
<!-- _backgroundImage: "linear-gradient(90deg, rgba(6,18,32,.96) 0%, rgba(6,18,32,.86) 38%, rgba(6,18,32,.35) 72%, rgba(6,18,32,.15) 100%), url('img/hero-hyderabad.jpg')" -->
<!-- _backgroundSize: cover -->

<div class="brand"><span class="logo"></span>Lake Protect</div>

<h1 style="margin-top:26px;max-width:780px">A weekly satellite watch that reaches the field, and <em>cases that hold up</em></h1>

<p class="lede">Lakes and government land in Telangana: screened from space, checked against the records, verified on the ground</p>

<div class="row" style="margin-top:30px;gap:10px"><span class="pill glass"><i class="ic ic-trophy"></i>TISC 2026</span><span class="pill glass"><i class="ic ic-waves"></i>Protecting Lakes and Government Land</span><span class="pill glass"><i class="ic ic-building"></i>Aanvi Infotech</span></div>

<div class="credit">Hyderabad up to the ORR · Sentinel-2 mosaic, Sep to Oct 2026<br>Contains modified Copernicus Sentinel data 2026</div>

<!--
Open with the promise, not the technology. We are not selling more alerts; we are selling cases that
hold up. The background is our own Sentinel-2 mosaic of Hyderabad, the same base map the app uses offline.
-->

---

<div class="kicker"><b>!</b>The problem</div>

## Hyderabad has lost *61%* of its lake area, and the watch has not kept up

<style scoped>
.prob { display: grid; grid-template-columns: 1.08fr 1fr; gap: 24px; }
.h61 { background: var(--ink); color: #fff; border-radius: 22px; padding: 26px 30px; display: flex; flex-direction: column; }
.h61 .n { font: 800 112px/1 "Manrope"; color: var(--cyan); letter-spacing: -.04em; }
.h61 .s { font-size: 19px; color: rgba(255,255,255,.88); margin-top: 8px; }
.drops { display: flex; gap: 8px; margin: 26px 0 12px; font-size: 50px; }
.drops .lost { color: rgba(255,255,255,.2); }
.drops .kept { color: var(--cyan); }
.h61 .k { font-size: 13.5px; color: rgba(255,255,255,.6); }
.h61 .w { margin-top: auto; display: flex; gap: 10px; align-items: center; font-size: 15.5px; color: rgba(255,255,255,.85); border-top: 1px solid rgba(255,255,255,.15); padding-top: 14px; }
.stats { display: grid; grid-template-rows: repeat(4, 1fr); gap: 12px; }
.stat { display: flex; align-items: center; gap: 16px; padding: 12px 18px; }
.stat .v { font: 800 28px/1 "Manrope"; }
.stat .l { font-size: 14.5px; color: var(--muted); line-height: 1.3; margin-top: 4px; }
</style>

<div class="prob fill">
<div class="h61"><div class="n">61%</div><div class="s">of Hyderabad's lake area lost between 1979 and 2024 (NRSC)</div><div class="drops"><i class="ic ic-droplet lost"></i><i class="ic ic-droplet lost"></i><i class="ic ic-droplet lost"></i><i class="ic ic-droplet lost"></i><i class="ic ic-droplet lost"></i><i class="ic ic-droplet lost"></i><i class="ic ic-droplets kept"></i><i class="ic ic-droplets kept"></i><i class="ic ic-droplets kept"></i><i class="ic ic-droplets kept"></i></div><div class="k">Each drop is about a tenth of the 1979 lake area</div><div class="w"><i class="ic ic-hourglass"></i>HYDRAA warns the remaining lakes could vanish within 15 years</div></div>
<div class="stats">
<div class="card stat"><div class="bi t-sky"><i class="ic ic-map"></i></div><div><div class="v">920</div><div class="l">water bodies mapped up to the ORR (TGRAC)</div></div></div>
<div class="card stat"><div class="bi t-sand"><i class="ic ic-cctv"></i></div><div><div class="v">656</div><div class="l">of them with no routine watch; CCTV covers 264 lakes</div></div></div>
<div class="card stat"><div class="bi t-violet"><i class="ic ic-file-check"></i></div><div><div class="v">23%</div><div class="l">of HMDA lakes have a final FTL notice (765 of 3,342)</div></div></div>
<div class="card stat"><div class="bi t-red"><i class="ic ic-gavel"></i></div><div><div class="v">Cases stall</div><div class="l">the High Court found boundaries "not clear" (Khajaguda)</div></div></div>
</div>
</div>

<!--
Sources: NRSC figures via Deccan Chronicle and NewsMeter; TGRAC survey; HMDA (January 2025); HYDRAA
CCTV (May 2026). All in the proposal and CONTEXT.md section 16.
The problem in one line: Telangana can already see its lakes. It lacks a recurring loop that turns each
new change into a dated, court-ready case, owned by a named officer with a deadline.
-->

---

<div class="kicker"><b>01</b>Encroachment and how we detect it</div>

## Encroachment takes six forms, and *each leaves a different trace*

<style scoped>
.types .card { display: flex; flex-direction: column; justify-content: center; gap: 14px; padding: 22px 24px; }
.types .bi { width: 60px; height: 60px; font-size: 31px; border-radius: 17px; }
.types .pill { font-size: 14px; padding: 6px 12px; }
.types .top { display: flex; align-items: center; gap: 14px; }
.types h3 { font-size: 21px; }
.types .sig { font-size: 16.5px; color: var(--muted); display: flex; gap: 8px; align-items: flex-start; line-height: 1.35; }
.types .sig .ic { color: var(--sky); margin-top: 2px; }
.types .by { display: flex; flex-wrap: wrap; gap: 6px; padding-top: 2px; }
.pill.s { background: var(--sky-50); color: var(--sky); }
.pill.c { background: var(--sand-50); color: #a8620a; }
.pill.v { background: var(--grey-50); color: var(--ink-3); }
</style>

<div class="g3 types fill" style="grid-auto-rows:1fr">
<div class="card"><div class="top"><div class="bi t-sand"><i class="ic ic-truck"></i></div><h3>Soil or debris dumped</h3></div><div class="sig"><i class="ic ic-eye"></i>Water turns to bare soil at the edge</div><div class="by"><span class="pill s"><i class="ic ic-satellite"></i>Weekly optical screen</span></div></div>
<div class="card"><div class="top"><div class="bi t-green"><i class="ic ic-shovel"></i></div><h3>Land cleared and levelled</h3></div><div class="sig"><i class="ic ic-eye"></i>Vegetation turns to bare soil</div><div class="by"><span class="pill s"><i class="ic ic-satellite"></i>Optical screen</span><span class="pill c"><i class="ic ic-zoom-in"></i>Sub-metre for plot lines</span></div></div>
<div class="card"><div class="top"><div class="bi t-violet"><i class="ic ic-fence"></i></div><h3>Sheds, fences, walls</h3></div><div class="sig"><i class="ic ic-eye"></i>Smaller than one 10 m pixel</div><div class="by"><span class="pill c"><i class="ic ic-zoom-in"></i>Sub-metre images</span><span class="pill v"><i class="ic ic-map-pin"></i>Field visit</span></div></div>
<div class="card"><div class="top"><div class="bi t-red"><i class="ic ic-building-2"></i></div><h3>Buildings in FTL or buffer</h3></div><div class="sig"><i class="ic ic-eye"></i>Built-up index and radar return rise</div><div class="by"><span class="pill s"><i class="ic ic-satellite"></i>Optical</span><span class="pill s"><i class="ic ic-radar"></i>Radar</span><span class="pill c"><i class="ic ic-zoom-in"></i>Footprint</span></div></div>
<div class="card"><div class="top"><div class="bi t-sky"><i class="ic ic-waves"></i></div><h3>Nalas and feeders blocked</h3></div><div class="sig"><i class="ic ic-eye"></i>Channel narrows or disappears</div><div class="by"><span class="pill c"><i class="ic ic-zoom-in"></i>Sub-metre images</span></div></div>
<div class="card"><div class="top"><div class="bi t-grey"><i class="ic ic-landmark"></i></div><h3>Government land occupied</h3></div><div class="sig"><i class="ic ic-eye"></i>New structures or fencing on a parcel</div><div class="by"><span class="pill s"><i class="ic ic-satellite"></i>Same signals</span><span class="pill v"><i class="ic ic-map"></i>Once the parcel boundary is official</span></div></div>
</div>

<!--
Be candid: sheds and walls under 10 m are never claimed from Sentinel. Water loss alone never alerts,
because season and drought shrink lakes too. Nala blocking and parcel occupation are on the roadmap:
they need sub-metre images and official parcel boundaries respectively.
-->

---

<div class="kicker"><b>01</b>Encroachment and how we detect it</div>

## Act while the change is *still reversible*

<style scoped>
.stages { position: relative; display: grid; grid-template-columns: repeat(5, 1fr); margin-top: 46px; }
.stages::before { content: ""; position: absolute; top: 50px; left: 10%; right: 10%; height: 5px; border-radius: 3px; background: linear-gradient(90deg, var(--teal) 0%, var(--teal) 50%, var(--sand) 70%, var(--red) 100%); }
.win { position: absolute; left: 1%; width: 58%; top: -30px; height: 22px; border: 2px solid var(--teal); border-bottom: none; border-radius: 12px 12px 0 0; }
.win span { position: absolute; top: -12px; left: 50%; transform: translateX(-50%); background: var(--bg); padding: 0 12px; font: 800 13px "Manrope"; letter-spacing: .14em; text-transform: uppercase; color: var(--teal); white-space: nowrap; }
.stage { text-align: center; position: relative; }
.stage .c { width: 104px; height: 104px; border-radius: 50%; margin: 0 auto; display: flex; align-items: center; justify-content: center; font-size: 46px; background: #fff; box-shadow: var(--shadow); color: var(--teal); border: 4px solid var(--teal); position: relative; z-index: 1; }
.stage.mid .c { color: #b86e0b; border-color: var(--sand); }
.stage.late .c { color: var(--red); border-color: var(--red); }
.stage .k { font: 800 12px "Manrope"; letter-spacing: .14em; color: var(--muted); margin-top: 14px; }
.stage h3 { font-size: 21px; margin-top: 2px; }
.stage p { font-size: 14.5px; color: var(--muted); margin: 6px 12px 0; line-height: 1.35; }
.ends { display: flex; justify-content: space-between; font: 800 13px "Manrope"; letter-spacing: .1em; text-transform: uppercase; margin: 18px 4% 0; }
.facts { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 24px; }
.facts .card { display: flex; gap: 14px; align-items: center; padding: 14px 18px; font-size: 15px; line-height: 1.35; }
</style>

<div class="stages">
<div class="win"><span>We alert here</span></div>
<div class="stage"><div class="c"><i class="ic ic-truck"></i></div><div class="k">STAGE 1</div><h3>Soil dumped</h3><p>Earth or debris tipped into the water</p></div>
<div class="stage"><div class="c"><i class="ic ic-shovel"></i></div><div class="k">STAGE 2</div><h3>Land levelled</h3><p>Plants cleared, ground flattened, plots pegged</p></div>
<div class="stage"><div class="c"><i class="ic ic-fence"></i></div><div class="k">STAGE 3</div><h3>Sheds and fences</h3><p>Sheds, compound walls and fencing go up</p></div>
<div class="stage mid"><div class="c"><i class="ic ic-building-2"></i></div><div class="k">STAGE 4</div><h3>Building rises</h3><p>Columns, slabs and walls</p></div>
<div class="stage late"><div class="c"><i class="ic ic-house"></i></div><div class="k">STAGE 5</div><h3>Family moves in</h3><p>Occupied, and the hardest to reverse</p></div>
</div>

<div class="ends"><span style="color:var(--teal)">Easiest to stop</span><span style="color:var(--red)">Hardest to reverse</span></div>

<div class="facts">
<div class="card"><div class="bi t-teal"><i class="ic ic-target"></i></div><div><b>Proposed target:</b> 60% of confirmed cases caught before a permanent structure</div></div>
<div class="card"><div class="bi t-red"><i class="ic ic-house"></i></div><div>HYDRAA has said it will not act against occupied homes, so <b>time matters</b></div></div>
<div class="card"><div class="bi t-sand"><i class="ic ic-calendar-clock"></i></div><div>Every alert carries a <b>dated bracket</b>: last clear and first changed image</div></div>
</div>

<!--
60% is a proposed target to agree with HYDRAA, not a result. Sheds and fences are caught by sub-metre
images or a field visit, not by 10 m Sentinel pixels.
-->

---

<div class="kicker"><b>01</b>Encroachment and how we detect it</div>

## Screen every lake weekly, *sharpen only where it matters*

<style scoped>
.tiers { display: grid; grid-template-columns: 1fr 44px 1fr 44px 1fr; align-items: stretch; }
.tier { padding: 22px 22px 20px; display: flex; flex-direction: column; gap: 9px; }
.tier .top { display: flex; align-items: center; justify-content: space-between; }
.tier .n { font: 800 13px "Manrope"; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); }
.tier h3 { font-size: 30px; }
.tier .w { font-size: 19px; font-weight: 700; }
.tier p { font-size: 16px; color: var(--muted); line-height: 1.4; }
.chev { display: flex; align-items: center; justify-content: center; color: #b9c7d4; font-size: 34px; }
.pix { margin-top: auto; display: flex; align-items: center; gap: 14px; font-size: 14.5px; color: var(--muted); }
.pix .g { width: 96px; height: 96px; border-radius: 14px; flex: none; }
.pix .g.coarse { background: repeating-linear-gradient(0deg, transparent 0 17px, rgba(255,255,255,.85) 17px 18.5px), repeating-linear-gradient(90deg, transparent 0 17px, rgba(255,255,255,.85) 17px 18.5px), linear-gradient(135deg, #3f86c2, #8fbf7a 55%, #d6b37a); }
.pix .g.fine { background: repeating-linear-gradient(0deg, transparent 0 2.5px, rgba(255,255,255,.55) 2.5px 3.2px), repeating-linear-gradient(90deg, transparent 0 2.5px, rgba(255,255,255,.55) 2.5px 3.2px), linear-gradient(135deg, #3f86c2, #8fbf7a 55%, #d6b37a); }
.pix .g.cam { background: var(--ink); color: #fff; display: flex; align-items: center; justify-content: center; gap: 4px; font-size: 28px; }
.idx { display: flex; gap: 10px; margin-top: 20px; align-items: center; flex-wrap: wrap; }
.idx .pill { background: #fff; color: var(--ink); box-shadow: var(--shadow); }
.idx .d { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.idx .lab { font: 800 12px "Manrope"; letter-spacing: .14em; color: var(--muted); margin-right: 4px; }
</style>

<div class="tiers fill">
<div class="card tier" style="border-top:5px solid var(--sky)"><div class="top"><span class="n">Tier 1</span><div class="bi t-sky"><i class="ic ic-satellite"></i></div></div><h3>Screen</h3><div class="w">Every lake, at least weekly</div><p>Sentinel-2 optical at 10 m, every 5 days; Sentinel-1 radar sees through monsoon cloud</p><div class="pix"><div class="g coarse"></div><span>One square is a<br><b>10 m</b> pixel</span></div></div>
<div class="chev"><i class="ic ic-chevron-right"></i></div>
<div class="card tier" style="border-top:5px solid var(--sand)"><div class="top"><span class="n">Tier 2</span><div class="bi t-sand"><i class="ic ic-zoom-in"></i></div></div><h3>Confirm</h3><div class="w">Priority cases only</div><p>Sub-metre images: Cartosat-3 through NRSC, or commercial at 0.3 to 0.5 m</p><div class="pix"><div class="g fine"></div><span>Same area at<br><b>0.3 to 0.5 m</b></span></div></div>
<div class="chev"><i class="ic ic-chevron-right"></i></div>
<div class="card tier" style="border-top:5px solid var(--ink)"><div class="top"><span class="n">Tier 3</span><div class="bi t-ink"><i class="ic ic-user-check"></i></div></div><h3>Verify</h3><div class="w">On the ground</div><p>A field officer with geotagged, hashed photos; CCTV and drones where they exist</p><div class="pix"><div class="g cam"><i class="ic ic-camera"></i><i class="ic ic-cctv"></i></div><span>Photo, place<br>and <b>time proved</b></span></div></div>
</div>

<div class="idx"><span class="lab">WHAT THE PIXELS MEASURE</span><span class="pill"><i class="d" style="background:#2f80c9"></i>Water · MNDWI</span><span class="pill"><i class="d" style="background:#23935a"></i>Vegetation · NDVI</span><span class="pill"><i class="d" style="background:#d6a35c"></i>Bare soil · BSI</span><span class="pill"><i class="d" style="background:#d2453f"></i>Built-up · NDBI</span><span class="pill"><i class="d" style="background:#6b46c1"></i>Radar · VV/VH</span></div>

<!--
The cost logic: sub-metre imagery for 900 lakes every week is unaffordable and unnecessary.
Medium-resolution optical and radar screen everything; sharp images are bought only for priority cases;
a person confirms on the ground. Each tier may use free, ISRO or commercial imagery, chosen per phase.
Radar matters most from June to September, when cloud cover over Hyderabad averages 79 to 89%.
-->

---

<div class="kicker"><b>01</b>Encroachment and how we detect it</div>

## Every alert *dates the change*

<style scoped>
.pair { display: grid; grid-template-columns: 404px 62px 404px 1fr; align-items: start; margin-top: 6px; }
.pair img { width: 100%; border-radius: 16px; box-shadow: var(--shadow); }
.cap { display: flex; align-items: center; gap: 10px; margin-top: 12px; font: 800 19px "Manrope"; }
.pill.sand { background: var(--sand-50); color: #a8620a; }
.mid { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 404px; color: var(--sand); font-size: 36px; gap: 4px; }
.mid span { font: 800 13px "Manrope"; color: var(--muted); text-align: center; line-height: 1.2; }
.side { padding-left: 24px; display: flex; flex-direction: column; gap: 13px; }
.side .row { font-size: 15px; line-height: 1.3; align-items: center; }
.leg { display: flex; flex-direction: column; gap: 7px; font-size: 13.5px; color: var(--muted); border-top: 1px solid var(--line); padding-top: 12px; margin-top: 4px; }
.leg .l { display: inline-block; width: 26px; border-top: 3px solid; vertical-align: middle; margin-right: 8px; }
</style>

<div class="pair">
<div><img src="img/candidate-before.png"><div class="cap"><span class="pill">LAST CLEAR</span>1 Jun 2026</div></div>
<div class="mid"><i class="ic ic-arrow-right"></i><span>70<br>days</span></div>
<div><img src="img/candidate-after.png"><div class="cap"><span class="pill sand">FIRST CHANGED</span>10 Aug 2026</div></div>
<div class="side">
<div class="row"><div class="bi sm t-sand"><i class="ic ic-shovel"></i></div><div>Water to <b>bare soil</b> inside the lake outline</div></div>
<div class="row"><div class="bi sm t-sky"><i class="ic ic-ruler"></i></div><div><b>2,700 sq m</b>, above the 1,000 sq m floor</div></div>
<div class="row"><div class="bi sm t-violet"><i class="ic ic-satellite"></i></div><div>Sentinel-2 L2A, 10 m, scene IDs on each image</div></div>
<div class="row"><div class="bi sm t-grey"><i class="ic ic-info"></i></div><div>A <b>candidate</b>: its cause is not verified</div></div>
<div class="leg"><div><i class="l" style="border-color:#2f80c9"></i>Lake outline</div><div><i class="l" style="border-color:#e05a4f;border-top-style:dashed"></i>Buffer zone</div><div><i class="l" style="border-color:#f2c230;border-top-style:dotted"></i>Changed pixels</div></div>
</div>
</div>

<!--
Real images from the prototype's own screen, not a mock-up. This is Kapra lake, one of our five tuning
lakes, where HYDRAA reported restoration works in 2026. That is the point: restoration looks like
encroachment from space, so the legal check looks for authorised works before anyone is sent out.
-->

---

<div class="kicker"><b>02</b>Solution architecture</div>

## One core decides *what deserves an officer's time*

<style scoped>
.arch { display: grid; grid-template-columns: 1fr 30px 1.55fr 30px 1fr; align-items: stretch; margin-top: -4px; }
.arch h4 { font: 800 12px "Manrope"; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); margin: 0 0 8px; }
.col { display: flex; flex-direction: column; gap: 7px; }
.ch { display: flex; align-items: center; gap: 11px; background: #fff; border-radius: 12px; box-shadow: var(--shadow); padding: 8px 11px; }
.ch b { display: block; font: 800 14.5px "Manrope"; line-height: 1.2; }
.ch span { display: block; font-size: 11.5px; color: var(--muted); line-height: 1.25; margin-top: 1px; }
.ar { display: flex; align-items: center; justify-content: center; color: var(--teal); font-size: 26px; }
.core { background: linear-gradient(180deg, #0f2a45, #0b1f33); border-radius: 20px; padding: 14px 16px; color: #fff; display: flex; flex-direction: column; gap: 8px; box-shadow: 0 20px 40px rgba(11,31,51,.25); }
.core .ttl { display: flex; align-items: center; gap: 10px; font: 800 13px "Manrope"; letter-spacing: .14em; text-transform: uppercase; color: var(--cyan); }
.core .ttl i.logo { width: 30px; height: 20px; background: var(--logo) center/contain no-repeat; }
.core .lb { font: 800 10.5px "Manrope"; letter-spacing: .16em; text-transform: uppercase; color: rgba(255,255,255,.55); margin-top: 2px; }
.flow { display: flex; align-items: stretch; gap: 4px; }
.nd { flex: 1; background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.12); border-radius: 10px; padding: 7px 4px; text-align: center; font-size: 11.5px; line-height: 1.2; display: flex; flex-direction: column; align-items: center; gap: 4px; }
.nd .ic { font-size: 19px; color: var(--cyan); }
.nd.key { background: var(--teal); border-color: var(--teal); font-weight: 700; }
.nd.key .ic { color: #fff; }
.fx { display: flex; align-items: center; color: rgba(255,255,255,.35); font-size: 12px; }
.base { display: flex; gap: 9px; align-items: center; background: rgba(255,255,255,.06); border-radius: 10px; padding: 7px 10px; font-size: 11.5px; line-height: 1.3; color: rgba(255,255,255,.8); }
.base .ic { font-size: 17px; color: var(--cyan); }
.base b { color: #fff; }
.loop { font-size: 12px; color: var(--cyan); text-align: center; font-weight: 700; }
</style>

<div class="arch">
<div class="col"><h4>Channels in</h4>
<div class="ch"><div class="bi sm t-sky"><i class="ic ic-satellite"></i></div><div><b>Satellite images</b><span>Optical and radar weekly; sub-metre on cue</span></div></div>
<div class="ch"><div class="bi sm t-teal"><i class="ic ic-smartphone"></i></div><div><b>Mobile field app</b><span>Officers: offline, Telugu, geotagged photos</span></div></div>
<div class="ch"><div class="bi sm t-green"><i class="ic ic-message-circle"></i></div><div><b>WhatsApp</b><span>Citizen reports: photo, pin, note</span></div></div>
<div class="ch"><div class="bi sm t-violet"><i class="ic ic-globe"></i></div><div><b>Web app</b><span>Citizen reports; 1070 and Praja Vani entered here</span></div></div>
<div class="ch"><div class="bi sm t-sand"><i class="ic ic-file-text"></i></div><div><b>Government records</b><span>FTL notices, permits, works, court cases, survey nos.</span></div></div>
<div class="ch"><div class="bi sm t-grey"><i class="ic ic-cctv"></i></div><div><b>Ground signals</b><span>900 CCTV cameras, lake guards</span></div></div>
</div>
<div class="ar"><i class="ic ic-chevron-right"></i></div>
<div class="core">
<div class="ttl"><i class="logo"></i>Lake Protect core</div>
<div class="lb">Process imagery</div>
<div class="flow"><div class="nd"><i class="ic ic-layers"></i>Catalogue each scene</div><div class="fx">›</div><div class="nd"><i class="ic ic-cpu"></i>Process it once</div><div class="fx">›</div><div class="nd"><i class="ic ic-map-pin"></i>Match every asset</div></div>
<div class="lb">Analyse</div>
<div class="flow"><div class="nd"><i class="ic ic-scan-search"></i>Detect change</div><div class="fx">›</div><div class="nd key"><i class="ic ic-scale"></i>Legal check</div><div class="fx">›</div><div class="nd"><i class="ic ic-gauge"></i>Set priority</div><div class="fx">›</div><div class="nd"><i class="ic ic-user-check"></i>Analyst review</div></div>
<div class="lb">Act</div>
<div class="flow"><div class="nd"><i class="ic ic-route"></i>Route, with a deadline</div><div class="fx">›</div><div class="nd"><i class="ic ic-map-pin"></i>Field check</div><div class="fx">›</div><div class="nd key"><i class="ic ic-file-lock"></i>Seal evidence</div></div>
<div class="base"><i class="ic ic-database"></i><div><b>Boundary register</b>, the system of record: core, FTL, buffer and survey numbers, certified and versioned · imagery record · case history</div></div>
<div class="base"><i class="ic ic-shield-check"></i><div><b>Every layer:</b> access by role and area · every action in a hash-chained log · missed deadlines escalate</div></div>
<div class="loop"><i class="ic ic-refresh-cw"></i> Field outcomes feed back to tune detection</div>
</div>
<div class="ar"><i class="ic ic-chevron-right"></i></div>
<div class="col"><h4>Portals out</h4>
<div class="ch"><div class="bi sm t-green"><i class="ic ic-users"></i></div><div><b>Citizen portal</b><span>Track a report by reference number: received, checked, closed with a reason</span></div></div>
<div class="ch"><div class="bi sm t-teal"><i class="ic ic-layout-dashboard"></i></div><div><b>Officer portal</b><span>Analyst desk, field tasks, case file, deadlines</span></div></div>
<div class="ch"><div class="bi sm t-ink"><i class="ic ic-file-lock"></i></div><div><b>Evidence pack</b><span>Sealed by SHA-256, with a Section 63(4) certificate</span></div></div>
<div class="ch"><div class="bi sm t-sky"><i class="ic ic-chart-column"></i></div><div><b>Leadership page</b><span>Monthly view, State to survey number</span></div></div>
<div class="ch"><div class="bi sm t-sand"><i class="ic ic-bell"></i></div><div><b>Notifications</b><span>Inbox, SMS, WhatsApp, daily email</span></div></div>
</div>
</div>

<!--
Anything that can signal a change comes in on the left; one core decides what deserves an officer's
time; portals and outputs carry the result.
Four things the core guarantees:
1. The legal check runs before routing: out-of-scope, legacy, authorised and court-held changes never
   reach a field team.
2. Boundary status gates action: only final or physically marked boundaries get the full officer path.
3. The citizen portal shows status only: never the accused, never owner names.
4. The field app is both a channel (photos in) and a portal (tasks out).
Heavy pieces (message brokers, Kubernetes, deep learning) come only when measured load needs them.
-->

---

<div class="kicker"><b>02</b>Solution architecture</div>

## Load each lake's boundary once from the State's records, *then watch it weekly*

<style scoped>
.steps { display: grid; grid-template-columns: 1fr 20px 1fr 20px 1fr 20px 1fr 20px 1fr; align-items: stretch; }
.stp { background: #fff; border-radius: 16px; box-shadow: var(--shadow); padding: 13px 14px 14px; display: flex; flex-direction: column; gap: 7px; }
.stp .hd { display: flex; align-items: center; justify-content: space-between; }
.stp .n { font: 800 12px "Manrope"; letter-spacing: .14em; color: var(--muted); }
.stp h3 { font-size: 18px; }
.stp p { font-size: 13.5px; color: var(--muted); line-height: 1.33; }
.chev { display: flex; align-items: center; justify-content: center; color: var(--teal); font-size: 20px; }
.low { display: grid; grid-template-columns: 1.15fr 1fr; gap: 18px; margin-top: 16px; }
.zones { display: grid; grid-template-columns: 250px 1fr; gap: 16px; align-items: center; padding: 14px 18px; }
.zones svg { width: 250px; height: 196px; display: block; }
.zt { font: 800 12px "Manrope"; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); margin-bottom: 2px; }
.zl { display: flex; flex-direction: column; gap: 8px; }
.zl .z { display: grid; grid-template-columns: 30px 1fr; gap: 10px; align-items: start; font-size: 13px; line-height: 1.3; color: var(--muted); }
.zl .z b { display: block; font: 800 14.5px "Manrope"; color: var(--ink); }
.zl .k { height: 0; border-top: 4px solid; margin-top: 8px; }
.wk { background: var(--ink); color: #fff; border-radius: 18px; padding: 16px 20px; display: flex; flex-direction: column; gap: 10px; box-shadow: 0 16px 34px rgba(11,31,51,.22); }
.wk .zt { color: var(--cyan); }
.wk .r { display: flex; gap: 12px; align-items: flex-start; font-size: 13px; line-height: 1.3; color: rgba(255,255,255,.72); }
.wk .r b { color: #fff; display: block; font: 700 14.5px "Manrope"; }
.wk .r .ic { font-size: 19px; color: var(--cyan); margin-top: 2px; }
</style>

<div class="steps">
<div class="stp"><div class="hd"><span class="n">STEP 1</span><div class="bi sm t-sand"><i class="ic ic-folder-open"></i></div></div><h3>Collect</h3><p>FTL notices, village maps, Record of Rights, Sethwar, 1954-55 Khasra Pahani</p></div>
<div class="chev"><i class="ic ic-chevron-right"></i></div>
<div class="stp"><div class="hd"><span class="n">STEP 2</span><div class="bi sm t-sky"><i class="ic ic-crosshair"></i></div></div><h3>Georeference</h3><p>Scanned sheets pinned to satellite control points; the error kept in metres</p></div>
<div class="chev"><i class="ic ic-chevron-right"></i></div>
<div class="stp"><div class="hd"><span class="n">STEP 3</span><div class="bi sm t-violet"><i class="ic ic-link"></i></div></div><h3>Link survey numbers</h3><p>Land category, extent and Bhudhaar for each parcel; no owner names</p></div>
<div class="chev"><i class="ic ic-chevron-right"></i></div>
<div class="stp"><div class="hd"><span class="n">STEP 4</span><div class="bi sm t-green"><i class="ic ic-git-compare"></i></div></div><h3>Reconcile</h3><p>Notice, village map and old imagery compared; gaps go to a boundary desk</p></div>
<div class="chev"><i class="ic ic-chevron-right"></i></div>
<div class="stp"><div class="hd"><span class="n">STEP 5</span><div class="bi sm t-teal"><i class="ic ic-badge-check"></i></div></div><h3>Certify, version</h3><p>Irrigation signs the FTL, Revenue the survey numbers; never overwritten</p></div>
</div>

<div class="low">
<div class="card zones">
<svg viewBox="14 20 226 154" xmlns="http://www.w3.org/2000/svg"><defs><path id="lkc" d="M70,96 C68,78 86,66 104,70 C114,60 134,56 148,64 C164,70 182,74 180,92 C192,100 186,118 168,120 C160,132 138,136 122,128 C106,134 82,126 80,112 C70,110 66,102 70,96 Z"/><clipPath id="lkclip"><use href="#lkc" transform="translate(126 96) scale(1.7) translate(-126 -96)"/></clipPath><linearGradient id="lkg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4b93cf"/><stop offset="1" stop-color="#22649f"/></linearGradient></defs><use href="#lkc" transform="translate(126 96) scale(1.7) translate(-126 -96)" fill="#f7f9fb" stroke="#8a99a8" stroke-width="1.6" stroke-dasharray="2 3" vector-effect="non-scaling-stroke"/><use href="#lkc" transform="translate(126 96) scale(1.43) translate(-126 -96)" fill="#fbe7e5" stroke="#d2453f" stroke-width="1.6" stroke-dasharray="5 4" vector-effect="non-scaling-stroke"/><use href="#lkc" transform="translate(126 96) scale(1.22) translate(-126 -96)" fill="#e6f0fa" stroke="#2f80c9" stroke-width="2.4" vector-effect="non-scaling-stroke"/><g clip-path="url(#lkclip)" stroke="#9fb0c0" stroke-width="1" fill="none"><path d="M58,10 L52,190"/><path d="M100,10 L95,190"/><path d="M150,10 L158,190"/><path d="M198,10 L192,190"/><path d="M10,58 L240,52"/><path d="M10,136 L240,142"/></g><g font-family="Inter, sans-serif" font-size="7.5" fill="#6b7a8c"><text x="192" y="76">87/A</text><text x="202" y="126">90</text><text x="118" y="44">101</text></g><use href="#lkc" fill="url(#lkg)"/><text x="126" y="99" text-anchor="middle" font-family="Manrope, sans-serif" font-weight="800" font-size="9" letter-spacing="1.2" fill="#fff">LAKE BED</text></svg>
<div class="zl"><div class="zt">What each lake holds</div>
<div class="z"><i class="k" style="border-color:#2f6fa8;border-top-width:8px;border-radius:3px"></i><div><b>Core</b>Survey numbers recorded as tank or shikam: government land</div></div>
<div class="z"><i class="k" style="border-color:#2f80c9"></i><div><b>FTL</b>The notified line; patta land inside stays private but cannot be built on</div></div>
<div class="z"><i class="k" style="border-color:#d2453f;border-top-style:dashed"></i><div><b>Buffer</b>30 m, or 9 m for small lakes; computed from the FTL</div></div>
<div class="z"><i class="k" style="border-color:#8a99a8;border-top-style:dotted"></i><div><b>Watch ring</b>100 m beyond, for early warning</div></div>
<div class="z"><i class="k" style="border-color:#9fb0c0;border-top-width:1.5px"></i><div><b>Parcels</b>Every survey number that crosses a zone</div></div>
</div>
</div>
<div class="wk"><div class="zt">Every week, against the baseline</div>
<div class="r"><i class="ic ic-calendar-check"></i><div><b>Cut-off: 19 July 2024</b>Policy date, to confirm with HYDRAA. Older change is recorded, not alerted</div></div>
<div class="r"><i class="ic ic-image"></i><div><b>Reference image frozen</b>Proof of what stood on each lake at the cut-off</div></div>
<div class="r"><i class="ic ic-satellite"></i><div><b>New optical and radar looks</b>Every lake, at least weekly</div></div>
<div class="r"><i class="ic ic-git-compare"></i><div><b>Compared twice</b>With the year before, to date the change; with the reference, to catch slow change</div></div>
<div class="r"><i class="ic ic-scale"></i><div><b>Legal check, then the alert</b>Zone, permits, works, court cases, boundary status</div></div>
</div>
</div>

<!--
The owner's plan in one slide: the State's own records become one register, the system of record,
before any alert is trusted. The pipeline is the one private land-record apps use (appendix A5), but
the source is the State's files and the departments certify the result. Detail: docs/asset-load.md.
Built today: append-only boundary versions, computed buffer and ring, cohorts, the dated bracket and
the legal check. Proposed: the core layer, certification step, frozen reference image and edge band.
The cut-off is the prototype's value (HYDRAA's July 2024 position); HYDRAA and counsel must confirm it.
-->

---

<div class="kicker"><b>02</b>Solution architecture</div>

## Officers get the picture, the dates and *what was checked*

<style scoped>
.prod { display: grid; grid-template-columns: 650px 196px 1fr; gap: 24px; align-items: start; }
.prod .shot { position: relative; }
.prod .shot .dot { position: absolute; }
.calls { display: flex; flex-direction: column; gap: 13px; }
.calls .row { align-items: flex-start; font-size: 13.5px; line-height: 1.35; color: var(--muted); gap: 10px; }
.calls b { display: block; font: 800 15px "Manrope"; color: var(--ink); margin-bottom: 1px; }
.tags { display: flex; flex-direction: column; gap: 6px; margin-top: 4px; }
.tags .pill { font-size: 12px; }
</style>

<div class="prod">
<div class="shot"><div class="browser"><div class="bar"><i></i><i></i><i></i><span>Analyst desk · Hyderabad lakes (real data)</span></div><img src="img/app-desk-kapra.jpg"></div><div class="dot" style="left:250px;top:110px">1</div><div class="dot" style="left:250px;top:330px">2</div><div class="dot" style="left:612px;top:222px">3</div></div>
<div class="shot"><div class="phone"><img src="img/app-field-te.jpg"></div><div class="dot" style="left:-10px;top:230px">4</div></div>
<div class="calls">
<div class="row"><div class="dot">1</div><div><b>Before and after</b>Same window, scene IDs and dates on every image</div></div>
<div class="row"><div class="dot">2</div><div><b>When it happened</b>Last clear and first changed, against the policy cut-off</div></div>
<div class="row"><div class="dot">3</div><div><b>What was checked</b>Boundary status, permits, works, court register</div></div>
<div class="row"><div class="dot">4</div><div><b>Field app in Telugu</b>Works offline; photos geotagged and hashed</div></div>
<div class="tags"><span class="pill"><i class="ic ic-satellite"></i>Desk: real alert, Kapra lake</span><span class="pill" style="background:var(--violet-50);color:var(--violet)"><i class="ic ic-smartphone"></i>Phone: labelled demo data</span></div>
</div>
</div>

<!--
Both screens are the running prototype, captured today. The desk shows a real alert on real Sentinel-2
images; it stays on the watch list because the outline is derived ("Estimated outline, not confirmed").
The phone shows the field app in Telugu on the fictional demo world; the purple band says so on screen.
-->

---

<div class="kicker"><b>03</b>Rules enforced</div>

## A legal check runs *before anyone moves*

<style scoped>
.lc { display: grid; grid-template-columns: 1fr 372px; gap: 24px; }
.ladder { display: flex; flex-direction: column; gap: 10px; }
.step { display: grid; grid-template-columns: 40px 1fr auto; align-items: center; gap: 14px; background: #fff; border-radius: 14px; box-shadow: var(--shadow); padding: 12px 16px 12px 12px; }
.step .q { font-size: 17.5px; font-weight: 600; line-height: 1.25; }
.step .q small { display: block; font-size: 12px; font-weight: 500; color: var(--muted); }
.res { font-size: 13px; font-weight: 700; padding: 6px 12px; border-radius: 999px; white-space: nowrap; display: inline-flex; gap: 6px; align-items: center; }
.res.closed { background: var(--grey-50); color: var(--grey); }
.res.hold { background: var(--sand-50); color: #a8620a; }
.res.watch { background: var(--violet-50); color: var(--violet); }
.res.go { background: var(--teal); color: #fff; }
.bs { padding: 18px 20px; display: flex; flex-direction: column; }
.bs h3 { font-size: 18px; margin-bottom: 6px; }
.ln { display: grid; grid-template-columns: 46px 1fr auto; align-items: center; gap: 10px; padding: 9px 0; border-top: 1px solid var(--line); font-size: 13.5px; line-height: 1.3; }
.ln i.s { display: block; width: 46px; border-top: 4px solid var(--sky); }
.big { font: 800 30px/1 "Manrope"; color: var(--teal); }
</style>

<div class="lc fill">
<div class="ladder">
<div class="step"><div class="bi sm t-grey"><i class="ic ic-map-pin-off"></i></div><div class="q">Outside the FTL, buffer and watch ring?</div><span class="res closed">Closed: out of scope</span></div>
<div class="step"><div class="bi sm t-grey"><i class="ic ic-calendar-x"></i></div><div class="q">First changed before the baseline date?</div><span class="res closed">Closed: legacy, logged</span></div>
<div class="step"><div class="bi sm t-grey"><i class="ic ic-file-check"></i></div><div class="q">Matches an authorised work or a valid permit?<small>Inside the FTL it is flagged for review</small></div><span class="res closed">Closed: authorised</span></div>
<div class="step"><div class="bi sm t-sand"><i class="ic ic-gavel"></i></div><div class="q">Live court matter?</div><span class="res hold">Hold for the legal officer</span></div>
<div class="step"><div class="bi sm t-violet"><i class="ic ic-eye"></i></div><div class="q">Lake not yet notified?</div><span class="res watch">Watch list</span></div>
<div class="step" style="box-shadow:0 0 0 2px var(--teal), var(--shadow)"><div class="bi sm t-teal"><i class="ic ic-user-check"></i></div><div class="q">Otherwise</div><span class="res go">Triage for analyst review</span></div>
<div class="note" style="margin-top:4px"><i class="ic ic-hash"></i> Each result stores the rule version, the boundary version and the records it matched</div>
</div>
<div class="card bs">
<h3>Boundary status decides what an alert may do</h3>
<div class="ln"><i class="s"></i><div>Physically marked, or final notice</div><span class="res go">Act</span></div>
<div class="ln"><i class="s" style="border-color:#7fb3e0"></i><div>Preliminary notice</div><span class="res go">Act</span></div>
<div class="ln"><i class="s" style="border-top-style:dashed"></i><div>Derived outline: the 99 real lakes today</div><span class="res watch">Verify</span></div>
<div class="ln"><i class="s" style="border-top-style:dotted;border-color:var(--grey)"></i><div>Survey number only</div><span class="res closed">Watch</span></div>
<div class="row" style="margin-top:auto;padding-top:12px;border-top:1px solid var(--line);gap:14px"><span class="big">23%</span><span class="note">of HMDA lakes have a final FTL notice (765 of 3,342), so we start where boundaries are certain</span></div>
</div>
</div>

<!--
This is what turns a detection into a case that survives the High Court. A live court matter moves any
alert to a legal hold, whatever the boundary status. Derived outlines go to a field check without an
officer path; survey-number-only land stays watch-only until a parcel boundary exists.
-->

---

<div class="kicker"><b>03</b>Rules enforced</div>

## Six rules *no one can switch off*

<style scoped>
.rules .card { display: flex; flex-direction: column; gap: 10px; padding: 20px 22px; }
.rules .top { display: flex; align-items: center; gap: 14px; }
.rules .num { font: 800 13px "Manrope"; color: var(--muted); letter-spacing: .12em; }
.rules h3 { font-size: 22px; }
.rules p { font-size: 16.5px; color: var(--muted); line-height: 1.38; }
.rules .how { margin-top: auto; display: flex; align-items: center; gap: 8px; font-size: 13.5px; font-weight: 700; color: var(--teal-600); background: var(--teal-50); border-radius: 9px; padding: 7px 10px; }
</style>

<div class="g3 rules fill" style="grid-auto-rows:1fr">
<div class="card"><div class="top"><div class="bi lg t-ink"><i class="ic ic-user-check"></i></div><div><div class="num">RULE 1</div><h3>Officers decide</h3></div></div><p>No legal labels, no advice on action: the system reports physical change</p><div class="how"><i class="ic ic-list-checks"></i>A test checks every English and Telugu string</div></div>
<div class="card"><div class="top"><div class="bi lg t-sky"><i class="ic ic-map"></i></div><div><div class="num">RULE 2</div><h3>Boundary status shown</h3></div></div><p>Every alert shows how certain its boundary is; only confirmed ones lead to action</p><div class="how"><i class="ic ic-list-checks"></i>Cohort gate in the workflow</div></div>
<div class="card"><div class="top"><div class="bi lg t-sand"><i class="ic ic-calendar-clock"></i></div><div><div class="num">RULE 3</div><h3>New change only</h3></div></div><p>Change first seen before the baseline date is closed as legacy and logged</p><div class="how"><i class="ic ic-list-checks"></i>Baseline 19 Jul 2024 for the real lakes</div></div>
<div class="card"><div class="top"><div class="bi lg t-violet"><i class="ic ic-eye-off"></i></div><div><div class="num">RULE 4</div><h3>Owner-blind</h3></div></div><p>Names appear only after a field check, only to authorised roles</p><div class="how"><i class="ic ic-list-checks"></i>Every view of a name is logged</div></div>
<div class="card"><div class="top"><div class="bi lg t-red"><i class="ic ic-users"></i></div><div><div class="num">RULE 5</div><h3>Nothing closes silently</h3></div></div><p>Two people to close; missed deadlines escalate by themselves</p><div class="how"><i class="ic ic-list-checks"></i>24 transition rules in a database trigger</div></div>
<div class="card"><div class="top"><div class="bi lg t-green"><i class="ic ic-badge-check"></i></div><div><div class="num">RULE 6</div><h3>No invented results</h3></div></div><p>Demo data is labelled fictional; no accuracy claimed before the blind backtest</p><div class="how"><i class="ic ic-list-checks"></i>Purple demo band on every demo screen</div></div>
</div>

<!--
These are enforced in code, not policy text. Rule 1: an automated wording test fails the build if words
such as "illegal" or "encroacher" appear in English or Telugu. Rule 5: closures as "not real", "false
alarm" or "no action" need two different people and a reason code. Rule 4 exists so an alert can never
be used to target or extort the people named.
-->

---

<div class="kicker"><b>03</b>Rules enforced</div>

## Controls cut 124,203 changed pixels to *58 candidates*

<style scoped>
.fn { display: grid; grid-template-columns: 1fr 318px; gap: 28px; }
.bars { display: flex; flex-direction: column; justify-content: space-between; }
.lbl { display: flex; align-items: center; gap: 8px; font-size: 15px; color: var(--muted); margin-bottom: 4px; }
.lbl .ic { color: var(--teal); }
.b { height: 50px; border-radius: 11px; display: flex; align-items: center; padding: 0 16px; color: #fff; font: 800 23px "Manrope"; box-shadow: var(--shadow); }
.b small { font: 600 13px "Inter"; opacity: .85; margin-left: 10px; }
.ctl { padding: 20px 22px; display: flex; flex-direction: column; justify-content: space-between; }
.ctl h3 { font-size: 17px; }
.ctl .row { font-size: 13.5px; line-height: 1.3; gap: 10px; }
.ctl .row b { display: block; font-size: 14px; color: var(--ink); }
</style>

<div class="fn fill">
<div class="bars">
<div><div class="lbl"><i class="ic ic-scan-search"></i>Changed pixels in the watched areas of 99 lakes</div><div class="b" style="width:100%;background:#7c93ab">124,203<small>pixels</small></div></div>
<div><div class="lbl"><i class="ic ic-droplets"></i>After water loss alone is set aside: it never alerts</div><div class="b" style="width:98%;background:#5f88b3">102,758<small>pixels</small></div></div>
<div><div class="lbl"><i class="ic ic-filter"></i>After persistence, season, drought, novelty and baseline</div><div class="b" style="width:77%;background:#3a7fb8">8,750<small>pixels</small></div></div>
<div><div class="lbl"><i class="ic ic-ruler"></i>Patches of 1,000 sq m or more</div><div class="b" style="width:42%;background:#1a8aa6">83<small>patches</small></div></div>
<div><div class="lbl"><i class="ic ic-radar"></i>After radar refused 25 building candidates</div><div class="b" style="width:38%;background:var(--teal)">58<small>candidates</small></div></div>
</div>
<div class="card ctl">
<h3>The controls, all required</h3>
<div class="row"><div class="bi sm"><i class="ic ic-repeat"></i></div><div><b>Persistence</b>Two looks at least 5 days apart, no reversal</div></div>
<div class="row"><div class="bi sm"><i class="ic ic-ruler"></i></div><div><b>Minimum area</b>1,000 sq m, about a quarter acre</div></div>
<div class="row"><div class="bi sm t-sand"><i class="ic ic-sun"></i></div><div><b>Season and drought</b>Same months in earlier years; worse than the 5 nearest lakes</div></div>
<div class="row"><div class="bi sm t-violet"><i class="ic ic-radar"></i></div><div><b>Buildings</b>Radar return must rise at least 3 dB</div></div>
<div class="row"><div class="bi sm t-grey"><i class="ic ic-calendar-x"></i></div><div><b>Baseline</b>Nothing first changed before the baseline date</div></div>
</div>
</div>

<div class="note" style="margin-top:12px"><i class="ic ic-info"></i> Real screen of 22 Nov 2026 · bar lengths on a log scale · each pixel is 10 m × 10 m · candidates are not findings: accuracy comes only from the blind backtest</div>

<!--
Real numbers from the prototype's screen of 99 Hyderabad lakes with images up to 22 November 2026.
58 candidate changes remained on 15 lakes (46 clearing, 11 soil fill, 1 building confirmed by radar at
+5.3 dB). All 58 sit on the watch list because the outlines are derived from OpenStreetMap.
Thresholds were tuned only on five separate tuning lakes and are frozen before the backtest.
Designed for the monsoon, not yet built: radar-only alerts marked "optical confirmation pending".
-->

---

<div class="kicker"><b>04</b>Technology and data</div>

## Optical, radar and sub-metre imagery, *each with one job*

<style scoped>
.sens .card { display: flex; flex-direction: column; gap: 8px; padding: 20px; }
.sens .top { display: flex; align-items: center; justify-content: space-between; }
.sens h3 { font-size: 21px; margin-top: 6px; }
.sens .res { font: 800 46px/1 "Manrope"; color: var(--teal); letter-spacing: -.02em; }
.sens .rv { font-size: 15.5px; font-weight: 600; color: var(--ink-3); }
.sens p { font-size: 16px; color: var(--muted); line-height: 1.38; }
.sens .src { margin-top: auto; font-size: 12px; font-weight: 700; color: var(--muted); border-top: 1px solid var(--line); padding-top: 9px; display: flex; gap: 6px; align-items: center; }
.strip { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 16px; }
.strip .card { display: flex; gap: 14px; align-items: center; padding: 14px 18px; font-size: 14.5px; line-height: 1.35; }
</style>

<div class="g4 sens fill">
<div class="card" style="border-top:5px solid var(--sky)"><div class="top"><div class="bi t-sky"><i class="ic ic-satellite"></i></div><span class="pill" style="background:var(--sky-50);color:var(--sky)">Optical</span></div><h3>Sentinel-2 L2A</h3><div class="res">10 m</div><div class="rv">Every 5 days</div><p>Weekly screen: water, vegetation, bare soil, built-up</p><div class="src"><i class="ic ic-globe"></i>Open data · ESA Copernicus</div></div>
<div class="card" style="border-top:5px solid var(--violet)"><div class="top"><div class="bi t-violet"><i class="ic ic-radar"></i></div><span class="pill" style="background:var(--violet-50);color:var(--violet)">Radar</span></div><h3>Sentinel-1</h3><div class="res">10 m</div><div class="rv">Sees through cloud</div><p>Confirms buildings; watches through the monsoon</p><div class="src"><i class="ic ic-globe"></i>Open data · ESA Copernicus</div></div>
<div class="card" style="border-top:5px solid var(--sand)"><div class="top"><div class="bi t-sand"><i class="ic ic-zoom-in"></i></div><span class="pill" style="background:var(--sand-50);color:#a8620a">Sub-metre</span></div><h3>Cartosat-3 or commercial</h3><div class="res">0.3–0.5 m</div><div class="rv">On demand</div><p>Confirms priority cases: footprints, sheds, plots</p><div class="src"><i class="ic ic-landmark"></i>ISRO via NRSC, or commercial</div></div>
<div class="card" style="border-top:5px solid var(--ink)"><div class="top"><div class="bi t-ink"><i class="ic ic-camera"></i></div><span class="pill" style="background:var(--grey-50);color:var(--ink)">Ground</span></div><h3>Field, CCTV, drones</h3><div class="res">On site</div><div class="rv">On every priority case</div><p>Verifies on the ground with geotagged, hashed photos</p><div class="src"><i class="ic ic-users"></i>State field teams</div></div>
</div>

<div class="strip">
<div class="card"><div class="bi t-sky"><i class="ic ic-map"></i></div><div><b>Boundaries:</b> official HMDA and HYDRAA FTL files replace the OpenStreetMap outlines used today</div></div>
<div class="card"><div class="bi t-teal"><i class="ic ic-layers"></i></div><div><b>Efficient:</b> read as cloud-optimised windows from Earth Search and Planetary Computer, never whole scenes</div></div>
</div>

<!--
Sentinel data is free and open under the Copernicus licence; every derived image carries the notice.
ISRO high-resolution imagery is free to government bodies under the Indian Space Policy 2023 (routing
through NRSC not yet confirmed). Sharing imagery at 30 cm or finer needs IN-SPACe authorisation, so
anything shared defaults to 50 cm.
-->

---

<div class="kicker"><b>04</b>Technology and data</div>

## An open, portable stack *the State can host and own*

<style scoped>
.sk { display: grid; grid-template-columns: 1fr 340px; gap: 26px; }
.slabs { display: flex; flex-direction: column; gap: 10px; }
.slab { flex: 1; display: grid; grid-template-columns: 56px 150px 1fr auto; align-items: center; gap: 16px; background: #fff; border-radius: 16px; box-shadow: var(--shadow); padding: 13px 18px; }
.slab h3 { font-size: 22px; }
.slab p { font-size: 16px; color: var(--muted); line-height: 1.38; }
.side { display: flex; flex-direction: column; gap: 14px; }
.side .card { flex: 1; padding: 18px 20px; display: flex; flex-direction: column; gap: 12px; }
.side .row { font-size: 15px; line-height: 1.3; gap: 10px; }
.side .row .ic { font-size: 17px; color: var(--muted); flex: none; }
.side h3 { font-size: 16px; display: flex; align-items: center; gap: 8px; }
</style>

<div class="sk fill">
<div class="slabs">
<div class="slab" style="border-left:6px solid var(--teal)"><div class="bi t-teal"><i class="ic ic-layout-dashboard"></i></div><h3>Apps</h3><p>Analyst desk in React and MapLibre · offline field app in English and Telugu · WeasyPrint evidence packs</p><span class="st built">Built</span></div>
<div class="slab" style="border-left:6px solid var(--sky)"><div class="bi t-sky"><i class="ic ic-server"></i></div><h3>Platform</h3><p>FastAPI modular monolith · PostgreSQL 16 with PostGIS 3.4 · append-only tables, hash-chained audit</p><span class="st built">Built</span></div>
<div class="slab" style="border-left:6px solid var(--violet)"><div class="bi t-violet"><i class="ic ic-scan-search"></i></div><h3>Detection</h3><p>Python, STAC catalogues, Rasterio, NumPy · rules versioned and hashed on every run</p><span class="st built">Built</span></div>
<div class="slab" style="border-left:6px solid var(--ink)"><div class="bi t-ink"><i class="ic ic-container"></i></div><h3>Hosting</h3><p>Docker on one server · State Data Centre or an Indian cloud · State owns all data · runs offline</p><span class="st built">Built</span></div>
</div>
<div class="side">
<div class="card" style="border-top:4px solid var(--sand)"><h3><span class="st pilot">Pilot</span>Adds</h3><div class="row"><i class="ic ic-key-round"></i>State single sign-on and MFA</div><div class="row"><i class="ic ic-shield"></i>Row-level security by department and area</div><div class="row"><i class="ic ic-hard-drive"></i>S3 storage with object lock</div><div class="row"><i class="ic ic-send"></i>Transactional outbox for reliable delivery</div></div>
<div class="card" style="border-top:4px solid var(--line)"><h3><span class="st later">Later</span>On measured need</h3><div class="row"><i class="ic ic-boxes"></i>Kubernetes or a message broker</div><div class="row"><i class="ic ic-brain"></i>Deep learning trained on officer-verified outcomes</div></div>
</div>
</div>

<!--
No licence fees in the core stack, and nothing that locks the State to one vendor or one imagery
provider. The whole demo, including maps, runs without internet. Deep learning is deliberately later:
there is no labelled Hyderabad training data today, and explainable index rules are easier to defend.
The pilot additions are designed, not built; say so if asked.
-->

---

<!-- _class: dark -->

![bg right:43%](img/lakes-tall.jpg)

<div class="kicker"><b>04</b>Running today</div>

## Already screening *99 real Hyderabad lakes*

<style scoped>
.mx { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 2px; }
.m { display: flex; align-items: center; gap: 14px; background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.1); border-radius: 16px; padding: 13px 16px; }
.m .bi { background: rgba(92,225,230,.14); color: var(--cyan); }
.m .v { font: 800 34px/1 "Manrope"; color: #fff; }
.m .l { font-size: 14px; color: rgba(255,255,255,.7); margin-top: 3px; line-height: 1.3; }
.cav { margin-top: 16px; display: flex; gap: 12px; align-items: center; font-size: 14px; color: rgba(255,255,255,.78); background: rgba(227,154,45,.12); border: 1px solid rgba(227,154,45,.35); border-radius: 12px; padding: 10px 14px; }
.cav .ic { color: var(--sand); font-size: 20px; }
.mapcap { position: absolute; right: 16px; bottom: 14px; width: 500px; text-align: right; font-size: 11px; color: rgba(255,255,255,.75); }
</style>

<div class="mx fill" style="grid-auto-rows:1fr">
<div class="m"><div class="bi"><i class="ic ic-waves"></i></div><div><div class="v">99</div><div class="l">lakes inside the ORR</div></div></div>
<div class="m"><div class="bi"><i class="ic ic-satellite"></i></div><div><div class="v">7,652</div><div class="l">clear looks since 2022</div></div></div>
<div class="m"><div class="bi"><i class="ic ic-calendar-check"></i></div><div><div class="v">14 days</div><div class="l">every lake seen clearly within</div></div></div>
<div class="m"><div class="bi"><i class="ic ic-timer"></i></div><div><div class="v">28 min</div><div class="l">full screen on one laptop</div></div></div>
<div class="m"><div class="bi"><i class="ic ic-scan-search"></i></div><div><div class="v">58</div><div class="l">candidate changes, all on the watch list</div></div></div>
<div class="m"><div class="bi"><i class="ic ic-circle-check"></i></div><div><div class="v">264</div><div class="l">automated tests pass: 249 API, 15 browser</div></div></div>
</div>

<div class="cav"><i class="ic ic-triangle-alert"></i><div>No accuracy is claimed until the blind backtest on 30 public cases</div></div>

<div class="note" style="margin-top:10px">Map: 99 watched lakes in cyan on a Sentinel-2 mosaic, Sep to Oct 2026 · Contains modified Copernicus Sentinel data 2026 · outlines © OpenStreetMap contributors</div>

<!--
Images up to 22 November 2026. Every one of the 99 lakes had a clear look within the last 14 days.
The first screen, from March 2022 to November 2026, took 28 minutes on a laptop CPU; a rerun from cache
takes minutes. No GPU is needed for the pilot. The officer loop (legal check, field app, evidence pack,
monthly page) runs end to end, offline, on a labelled fictional demo world. Offer the live demo here.
-->

---

<div class="kicker"><b>→</b>What happens next</div>

## Each phase must *earn the next*

<style scoped>
.tl { position: relative; display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; margin-top: 4px; }
.tl::before { content: ""; position: absolute; left: 4%; right: 8%; top: 36px; height: 5px; border-radius: 3px; background: linear-gradient(90deg, var(--teal), var(--sky)); }
.ph .c { width: 76px; height: 76px; border-radius: 50%; background: #fff; border: 4px solid var(--teal); display: flex; align-items: center; justify-content: center; font-size: 34px; color: var(--teal); position: relative; z-index: 1; margin-bottom: 10px; box-shadow: var(--shadow); }
.ph .when { font: 800 13px "Manrope"; letter-spacing: .12em; text-transform: uppercase; color: var(--teal-600); }
.ph h3 { font-size: 25px; margin: 3px 0 6px; }
.ph p { font-size: 16px; color: var(--muted); line-height: 1.38; min-height: 46px; }
.ph .gate { display: flex; gap: 8px; align-items: flex-start; font-size: 14.5px; line-height: 1.3; margin-top: 12px; background: #fff; box-shadow: var(--shadow); border-radius: 10px; padding: 9px 11px; }
.ph .gate .ic { color: var(--teal); font-size: 16px; margin-top: 1px; }
.ph .cost { margin-top: 10px; font: 800 21px "Manrope"; color: var(--ink); }
.ph .cost span { font: 600 12px "Inter"; color: var(--muted); }
.tg { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-top: 8px; }
.tg .card { padding: 12px 14px; }
.tg .v { font: 800 26px/1 "Manrope"; color: var(--teal); }
.tg .l { font-size: 12.5px; color: var(--muted); line-height: 1.3; margin-top: 5px; }
.tgh { margin-top: 14px; font: 800 12px "Manrope"; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); }
.stop { margin-top: 14px; display: flex; gap: 14px; align-items: center; background: var(--red-50); color: #8f2b27; border-radius: 14px; padding: 11px 18px; font-size: 14.5px; }
.stop .ic { font-size: 22px; }
</style>

<div class="tl">
<div class="ph"><div class="c"><i class="ic ic-flask-conical"></i></div><div class="when">Dec 2026</div><h3>Blind backtest</h3><p>30 public cases on archived images</p><div class="gate"><i class="ic ic-lock"></i>Gate: at least 21 of 30 flagged before public action</div><div class="cost">No cost</div></div>
<div class="ph"><div class="c"><i class="ic ic-handshake"></i></div><div class="when">Jan to Mar 2027</div><h3>Demonstration</h3><p>About 20 recovered assets with HYDRAA</p><div class="gate"><i class="ic ic-lock"></i>Gate: officer named, boundaries shared</div><div class="cost">No cost</div></div>
<div class="ph"><div class="c"><i class="ic ic-rocket"></i></div><div class="when">Apr to Sep 2027</div><h3>Paid pilot</h3><p>100 lakes and 10 parcels, through one monsoon</p><div class="gate"><i class="ic ic-lock"></i>Gate: pilot targets met</div><div class="cost">₹40–60 lakh</div></div>
<div class="ph"><div class="c" style="border-color:var(--sky);color:var(--sky)"><i class="ic ic-map"></i></div><div class="when" style="color:var(--sky)">From Oct 2027</div><h3>Core urban region</h3><p>900+ lakes and recovered assets</p><div class="gate"><i class="ic ic-lock"></i>Gate: renewal funded</div><div class="cost">₹4.5–9.5 crore <span>a year</span></div></div>
</div>

<div class="tgh">Pilot targets: measured, not promised, to agree with HYDRAA · costs are indicative estimates, not quotes</div>

<div class="tg"><div class="card"><div class="v">70%</div><div class="l">field-confirmed precision by pilot month 6</div></div><div class="card"><div class="v">14 days</div><div class="l">median from first change to field check (30 in monsoon)</div></div><div class="card"><div class="v">60%</div><div class="l">of confirmed cases caught before a permanent structure</div></div><div class="card"><div class="v">100%</div><div class="l">of alerts with a named owner and a closure reason</div></div><div class="card"><div class="v">90%</div><div class="l">of evidence packs accepted by legal without rework</div></div></div>

<div class="stop"><i class="ic ic-octagon-x"></i><div><b>We stop if</b> the backtest flags under 15 of 30, precision is under 50% at pilot month 4, or there is no official boundary access by March 2027</div></div>

<!--
The ask: a named officer and official boundary files for the demonstration on recovered assets.
Pilot targets, to agree with HYDRAA, not results: 70% field-confirmed precision by month 6; 14 days
median from first change to field check (30 in monsoon); 60% of confirmed cases caught before a
permanent structure; 100% of alerts with a named owner and closure reason; 90% of evidence packs
accepted by legal without rework. One year of watch for the core urban region costs less than one acre
of recovered land (HYDRAA's estimate for Ailapur: ₹17.4 crore an acre).
-->

---

<!-- _class: dark hero -->
<!-- _paginate: false -->
<!-- _backgroundImage: "linear-gradient(90deg, rgba(6,18,32,.95) 0%, rgba(6,18,32,.82) 45%, rgba(6,18,32,.4) 100%), url('img/lakes-wide.jpg')" -->
<!-- _backgroundSize: cover -->

<style scoped>
.chain { display: flex; align-items: center; gap: 12px; margin-top: 34px; }
.chain .s { display: flex; align-items: center; gap: 10px; background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.2); border-radius: 14px; padding: 11px 16px; font: 700 16px "Manrope"; color: #fff; }
.chain .s .ic { color: var(--cyan); font-size: 22px; }
.chain > .ic { color: rgba(255,255,255,.45); font-size: 20px; }
</style>

<div class="brand"><span class="logo"></span>Lake Protect</div>

<h1 style="margin-top:24px;max-width:860px">Recovered land stays recovered, and every action <em>stands up in court</em></h1>

<div class="chain"><div class="s"><i class="ic ic-badge-check"></i>Certified boundaries</div><i class="ic ic-chevron-right"></i><div class="s"><i class="ic ic-satellite"></i>Weekly watch</div><i class="ic ic-chevron-right"></i><div class="s"><i class="ic ic-scale"></i>Legal check</div><i class="ic ic-chevron-right"></i><div class="s"><i class="ic ic-map-pin"></i>Field visit</div><i class="ic ic-chevron-right"></i><div class="s"><i class="ic ic-file-lock"></i>Sealed case file</div></div>

<div class="credit">99 watched lakes · Contains modified Copernicus Sentinel data 2026 · outlines © OpenStreetMap contributors</div>

<!--
Reprise the commercial: Telangana can see its lakes. Lake Protect turns each new change into a dated,
checked, field-verified case with a named officer and a deadline, sealed so it holds up in court.
Pause for questions; use the appendix.
-->

---

<div class="kicker"><b>A1</b>Appendix</div>

## Detection rules, and *what is live today*

<style scoped>
.rl { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 18px; }
.r { display: grid; grid-template-columns: 44px 1fr auto; gap: 12px; align-items: center; background: #fff; border-radius: 14px; box-shadow: var(--shadow); padding: 10px 14px; }
.r b { display: block; font: 800 17px "Manrope"; }
.r span.d { font-size: 14.5px; color: var(--muted); line-height: 1.3; }
.r .sts { display: flex; flex-direction: column; gap: 4px; align-items: flex-end; }
</style>

<div class="rl fill" style="grid-auto-rows:1fr">
<div class="r"><div class="bi sm t-sky"><i class="ic ic-droplets"></i></div><div><b>R01 Water spread</b><span class="d">Context only: water loss alone never alerts</span></div><div class="sts"><span class="st built">Built</span></div></div>
<div class="r"><div class="bi sm t-red"><i class="ic ic-building-2"></i></div><div><b>R02/R03 Building in FTL or buffer</b><span class="d">10 m screen with radar; sub-metre confirm</span></div><div class="sts"><span class="st built">Built</span><span class="st pilot">Pilot</span></div></div>
<div class="r"><div class="bi sm t-sand"><i class="ic ic-truck"></i></div><div><b>R04 Soil fill or dumping</b><span class="d">Water to bare soil at the lake edge</span></div><div class="sts"><span class="st built">Built</span></div></div>
<div class="r"><div class="bi sm t-grey"><i class="ic ic-landmark"></i></div><div><b>R05 Government parcel occupation</b><span class="d">Surveyed agency land, from 2028</span></div><div class="sts"><span class="st later">Later</span></div></div>
<div class="r"><div class="bi sm t-green"><i class="ic ic-shovel"></i></div><div><b>R06 Vegetation clearing</b><span class="d">Vegetation to bare soil, against last year</span></div><div class="sts"><span class="st built">Built</span></div></div>
<div class="r"><div class="bi sm t-grey"><i class="ic ic-construction"></i></div><div><b>R07 Levelling or excavation volume</b><span class="d">Drone or stereo height models</span></div><div class="sts"><span class="st later">Later</span></div></div>
<div class="r"><div class="bi sm t-grey"><i class="ic ic-waves"></i></div><div><b>R08/R09 Nala, feeder and road</b><span class="d">Sub-metre images for narrow channels</span></div><div class="sts"><span class="st later">Later</span></div></div>
<div class="r"><div class="bi sm t-violet"><i class="ic ic-message-circle"></i></div><div><b>R10 Citizen report check</b><span class="d">Match to an asset, recheck the latest look</span></div><div class="sts"><span class="st pilot">Pilot</span></div></div>
</div>

<div class="note" style="margin-top:16px"><i class="ic ic-hash"></i> Rules live in a versioned file (detect-v1); its SHA-256 is recorded on every run, so any case shows exactly which rules produced it</div>

---

<div class="kicker"><b>A2</b>Appendix</div>

## Boundary status decides *what an alert may do*

<style scoped>
.co { display: flex; flex-direction: column; gap: 9px; }
.co .c { flex: 1; }
.c { display: grid; grid-template-columns: 46px 1fr 220px 270px; gap: 16px; align-items: center; background: #fff; border-radius: 14px; box-shadow: var(--shadow); padding: 9px 16px; font-size: 16.5px; }
.c .L { width: 40px; height: 40px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font: 800 19px "Manrope"; background: var(--ink); color: #fff; }
.c .bd { display: flex; align-items: center; gap: 10px; font-size: 14px; color: var(--muted); }
.c .bd i { display: block; width: 40px; border-top: 4px solid var(--sky); }
.c .res { font-size: 13px; font-weight: 700; padding: 6px 12px; border-radius: 999px; justify-self: start; }
.go { background: var(--teal); color: #fff; }
.ver { background: var(--violet-50); color: var(--violet); }
.wat { background: var(--grey-50); color: var(--grey); }
.hd { display: grid; grid-template-columns: 46px 1fr 220px 270px; gap: 16px; padding: 0 16px; font: 800 11.5px "Manrope"; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); }
</style>

<div class="co fill">
<div class="hd"><span></span><span>Asset</span><span>Boundary</span><span>Alert may</span></div>
<div class="c"><div class="L">A</div><div>Recovered land in State hands</div><div class="bd"><i></i>Physically marked</div><span class="res go">Act: full officer path</span></div>
<div class="c"><div class="L">B</div><div>Lake with final notification</div><div class="bd"><i></i>Final notice</div><span class="res go">Act</span></div>
<div class="c"><div class="L">C</div><div>Lake with preliminary notification</div><div class="bd"><i style="border-color:#7fb3e0"></i>Preliminary</div><span class="res ver">Verify: field check, no officer path</span></div>
<div class="c"><div class="L" style="background:var(--grey)">D</div><div>Lake without notification</div><div class="bd"><i style="border-top-style:dashed"></i>Derived</div><span class="res wat">Watch: logged, no field action</span></div>
<div class="c"><div class="L" style="background:var(--grey)">E</div><div>Surveyed agency land</div><div class="bd"><i style="border-color:var(--sand)"></i>Agency survey</div><span class="res go">Act, via the owning agency (2028)</span></div>
<div class="c"><div class="L" style="background:var(--grey)">F</div><div>Revenue land by survey number only</div><div class="bd"><i style="border-top-style:dotted;border-color:var(--grey)"></i>Survey number</div><span class="res wat">Watch</span></div>
</div>

<div class="note" style="margin-top:14px"><i class="ic ic-gavel"></i> A live court matter moves any alert to a legal hold, whatever the cohort · the 99 real lakes today are cohort D</div>

---

<div class="kicker"><b>A3</b>Appendix</div>

## What exists, what the pilot adds, *what comes later*

<style scoped>
.bpl { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
.bpl .card { padding: 22px 22px; display: flex; flex-direction: column; gap: 15px; }
.bpl h3 { display: flex; align-items: center; gap: 10px; font-size: 19px; margin-bottom: 4px; }
.bpl .row { align-items: flex-start; font-size: 15.5px; line-height: 1.35; gap: 10px; }
.bpl .row .ic { font-size: 18px; flex: none; margin-top: 1px; }
.b .ic { color: var(--green); }
.p .ic { color: #b86e0b; }
.l .ic { color: var(--grey); }
</style>

<div class="bpl fill">
<div class="card b" style="border-top:5px solid var(--green)"><h3><span class="st built">Built</span>Running today</h3>
<div class="row"><i class="ic ic-circle-check"></i>Sentinel-2 and radar screen on 99 real lakes</div>
<div class="row"><i class="ic ic-circle-check"></i>Legal check, 24-rule state machine, escalation</div>
<div class="row"><i class="ic ic-circle-check"></i>Offline field app, English and Telugu</div>
<div class="row"><i class="ic ic-circle-check"></i>Sealed evidence packs and a verify tool</div>
<div class="row"><i class="ic ic-circle-check"></i>Role checks, hash-chained audit</div>
<div class="row"><i class="ic ic-circle-check"></i>Monthly page; citizen signals table</div>
</div>
<div class="card p" style="border-top:5px solid var(--sand)"><h3><span class="st pilot">Pilot</span>2027</h3>
<div class="row"><i class="ic ic-circle-dashed"></i>Blind backtest; sub-metre confirmation</div>
<div class="row"><i class="ic ic-circle-dashed"></i>Deadlines agreed with HYDRAA</div>
<div class="row"><i class="ic ic-circle-dashed"></i>Counsel-reviewed Section 63(4) certificate</div>
<div class="row"><i class="ic ic-circle-dashed"></i>WhatsApp and web intake in English, Telugu and Urdu</div>
<div class="row"><i class="ic ic-circle-dashed"></i>State SSO, MFA, row-level security</div>
<div class="row"><i class="ic ic-circle-dashed"></i>S3 object lock, transactional outbox</div>
</div>
<div class="card l" style="border-top:5px solid var(--line)"><h3><span class="st later">Later</span>On measured need</h3>
<div class="row"><i class="ic ic-circle"></i>Deep learning on verified outcomes</div>
<div class="row"><i class="ic ic-circle"></i>Per-category policies for all public land</div>
<div class="row"><i class="ic ic-circle"></i>Drone height models for excavation</div>
<div class="row"><i class="ic ic-circle"></i>Key management, high availability</div>
<div class="row"><i class="ic ic-circle"></i>Kubernetes or a message broker</div>
</div>
</div>

<!--
Proposal slide 26 lists the statewide registry, department security, S3 storage and the outbox as built;
they are designed, not built. This slide is the accurate version: use it if the jury asks.
-->

---

<div class="kicker"><b>A4</b>Appendix</div>

## Leaders see *one page a month*, from State to survey number

<style scoped>
.mp { display: grid; grid-template-columns: 720px 1fr; gap: 28px; align-items: start; }
.mp .calls { display: flex; flex-direction: column; gap: 14px; }
.mp .row { align-items: flex-start; font-size: 14.5px; line-height: 1.35; color: var(--muted); }
.mp .row b { display: block; font: 800 16px "Manrope"; color: var(--ink); }
</style>

<div class="mp">
<div class="browser"><div class="bar"><i></i><i></i><i></i><span>Monthly page · demo world (fictional)</span></div><img src="img/app-monthly.jpg"></div>
<div class="calls">
<div class="row"><div class="bi sm t-sky"><i class="ic ic-chart-column"></i></div><div><b>Five monthly figures</b>Watched, new, seen on site, actions, overdue</div></div>
<div class="row"><div class="bi sm t-red"><i class="ic ic-bell"></i></div><div><b>Overdue, by who must act</b>Late work surfaces on its own</div></div>
<div class="row"><div class="bi sm t-teal"><i class="ic ic-map"></i></div><div><b>Every number opens its cases</b>No bulk export; every view logged</div></div>
<div class="row"><div class="bi sm t-violet"><i class="ic ic-printer"></i></div><div><b>Print one page</b>For the monthly review meeting</div></div>
</div>
</div>

---

<div class="kicker"><b>A5</b>Appendix</div>

## Survey-number maps: *the private apps' method, the State's own source*

<style scoped>
.cmp { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.cmp .card { padding: 18px 22px; display: flex; flex-direction: column; gap: 13px; }
.cmp h3 { display: flex; align-items: center; gap: 10px; font-size: 20px; margin-bottom: 2px; }
.cmp .it { display: grid; grid-template-columns: 38px 1fr; gap: 12px; align-items: center; font-size: 15px; line-height: 1.33; color: var(--muted); }
.cmp .it b { color: var(--ink); }
.cmp .ft { margin-top: auto; font-size: 14.5px; border-radius: 10px; padding: 10px 13px; display: flex; gap: 10px; align-items: flex-start; line-height: 1.35; }
.cmp .ft .ic { font-size: 18px; margin-top: 1px; }
.ft.bad { background: var(--grey-50); color: var(--ink-3); }
.ft.good { background: var(--teal-50); color: var(--teal-600); }
.gap { margin-top: 14px; display: flex; gap: 16px; align-items: center; background: var(--violet-50); color: #4a2f91; border-radius: 14px; padding: 12px 18px; font-size: 15px; line-height: 1.35; }
.gap .v { font: 800 30px/1 "Manrope"; color: var(--violet); }
</style>

<div class="cmp fill">
<div class="card" style="border-top:5px solid var(--line)"><h3><div class="bi sm t-grey"><i class="ic ic-smartphone"></i></div>Private land-record apps</h3>
<div class="it"><div class="bi sm t-grey"><i class="ic ic-folder-open"></i></div><div><b>Gather</b> village maps and records from portals, offices and old scans</div></div>
<div class="it"><div class="bi sm t-grey"><i class="ic ic-crosshair"></i></div><div><b>Pin</b> each scanned sheet onto satellite images</div></div>
<div class="it"><div class="bi sm t-grey"><i class="ic ic-hash"></i></div><div><b>Key</b> every plot by district, mandal, village and survey number</div></div>
<div class="it"><div class="bi sm t-grey"><i class="ic ic-search"></i></div><div><b>Sell look-ups</b> from a point to a survey number; certified copies fetched by agents</div></div>
<div class="ft bad"><i class="ic ic-triangle-alert"></i><div>Useful to a buyer, but uncertified: no court will take it as a lake boundary</div></div>
</div>
<div class="card" style="border-top:5px solid var(--teal)"><h3><div class="bi sm t-teal"><i class="ic ic-shield-check"></i></div>Lake Protect</h3>
<div class="it"><div class="bi sm"><i class="ic ic-handshake"></i></div><div><b>Ask through HYDRAA</b>: CCLA (Survey and Land Records), Irrigation and HMDA</div></div>
<div class="it"><div class="bi sm t-sky"><i class="ic ic-map"></i></div><div><b>Start from the State's own vectors</b>: most village maps reported digitised; re-surveyed villages added as they arrive</div></div>
<div class="it"><div class="bi sm t-violet"><i class="ic ic-eye-off"></i></div><div><b>Same keys, plus Bhudhaar</b>: land category and extent; owner names withheld</div></div>
<div class="it"><div class="bi sm t-green"><i class="ic ic-badge-check"></i></div><div><b>Certified by the departments</b>, versioned and hashed</div></div>
<div class="ft good"><i class="ic ic-gavel"></i><div>The certified government map is the only boundary that can start an action</div></div>
</div>
</div>

<div class="gap"><div class="v">2,577</div><div>of HMDA's 3,342 lakes have no final FTL notice. Their outlines, derived from imagery, run in watch mode, and the file built for each can support the Lake Protection Committee's notification work</div></div>

<!--
Private apps such as Landeed and Telangana LandGrid sell survey-number maps; Landeed says its village
maps come from the District Survey and Land Records office through the Bhu Bharati back end. None
publishes its method; the left column is our reading of what they offer. We copy the method, not
the source: no scraping, no bought maps. The State reports most village maps digitised and
georeferenced (to confirm with Survey and Land Records). 2,577 = 3,342 minus the 765 with a final
notice (HMDA, January 2025). Detail: docs/asset-load.md.
-->
