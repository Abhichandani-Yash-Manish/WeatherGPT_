# 101 — Satisfactory farm answers: the window, the district, the daily product and the dose label

17 September 2026, after the user reported that farming questions were still answered poorly or not at all.
Two questions were reproduced exactly as asked, and four more defects were found behind them. Every repair
below carries a check that fails without it, and the two questions now answer.

## 1. The two reported questions

**Gujarati:** "હું બનાસકાંઠા જિલ્લાના ડીસામાં બાજરી ઉગાડું છું. આગામી ત્રણ દિવસમાં કેટલો વરસાદ પડવાની આગાહી છે?"
(I grow bajra in Deesa, Banaskantha; how much rain is forecast in the next three days?) — was **"No verified
evidence for this", 0 of 1 tasks**, with "hourly detail supports up to 48 hours".

**Hindi/Hinglish:** "Mera farm Chhindwara district mein hai, maize 45 din ki hai. Kal 6 se 9 AM ka rain chance
aur wind speed batao, aur latest official advisory ka source bhi do." — was **partly answered**: the forecast
task asked "which village or town within Chhindwara?", the window had collapsed to the single hour 09:00, and
the advisory half served pesticide dose sentences as the district's advice.

## 2. The defects and their causes

**A. A three-day rainfall question was routed to the 48-hour hourly product.** `capabilities.forecast_tool`
read *any* window whose endpoints were not on the half-hour as a clock-time question — and midnight is not
minute 30 — so "the next three days" went to the hourly product and was refused. The rule now reads the
window: an explicit clock window, an hourly-only parameter (probability, gusts, visibility, apparent
temperature), a timeline/onset operation or a continued S62 preference gets the hourly product; a window
longer than the hourly horizon gets the daily summary; everything else is a daily question.

**B. The daily path could not express one whole day.** The answer grammar rejected equal clock times, so a
source day (00:30 → 00:30) was inexpressible and each day was read as 23 hours, which then split a source
rain interval and returned "an exact total is unavailable". Equal clock times now read as the 24 hours that
follow them — one complete source day — and the daily path aligns a whole-day window to the source's own
:30 days (one day or a whole number of days, with the days named in a note) and splits its pieces by source
day rather than by 23 hours.

**C. "6 se 9 AM" lost its first hour.** The planner read a spoken hour range as its second hour (`spoken`),
so a three-hour window became the instant 09:00 and the answer covered one hour. A spoken range — "6 se 9
AM", "6 to 9 am", "6-9 am", "6 AM se 9 AM" — is now read as the window from the first hour to the second,
in the meridiem both carry, before the single-hour rule runs.

**D. A district was not a place the engine would read.** A district question was answered with "Which village
or town within X?" — which is a legitimate caution but left the most common farmer phrasing unanswerable. The
place catalogue records each district's own administrative centre (GeoNames keeps the seat with its district
in `admin2`: Chhindwāra, Chhindwāra, Madhya Pradesh), so a district now reads at that seat **and says so**:
the note names the seat, states that a district is not a point, and states that it is not a district-wide map.
A catalogue that cannot name a seat (or an older stub) keeps the clarification, and no nearby city is ever
substituted.

**E. Dose instructions were served as advice.** Three maize sentences naming doses were quoted as the
district's advice for a farmer's maize question. `label_text_only` now also recognises a sentence that
names a measure *and* instructs an application ("Spray Spinosad 45 SC 0.3 ml … to protect the crop"), and the
live district-bulletin path — which had its own renderer and no label rule — reports those passages under
"Printed product-label or dose text in this bulletin (a label, not advice)", with the statement that no dose
is chosen, adjusted or endorsed here. Page furniture is stripped from the quarantined quotes too.

**F. A partial window was disclosed without its reason.** A clock window rarely sits on the source's :30
grid, so 06:00–09:00 is covered from 06:30. The answer now says which part of the window the product covers
and that the remaining minutes are not in it, instead of a bare "some part is incomplete".

## 3. What the two questions answer now

| Question | Before | After |
| --- | --- | --- |
| Gujarati, three days of rain for Deesa | "No verified evidence for this", 0 of 1 tasks | **answered**, 1 of 1: one day per source day — 0.6 mm (19 Sep 00:30→20 Sep 00:30), 0.1 mm (20→21), 0.0 mm (21→22) IST, with the alignment note and "model forecast, not an observation or a district average" |
| Hindi/Hinglish, 6–9 AM rain chance + wind + advisory for Chhindwara | partly answered: asked for a village; window 09:00–10:00; dose text served as advice | **both tasks answered**: rain chance per hour (0–2 %, maximum 2 % in 07:30–08:30) and wind 3.6–4.5 km/h for the covered window, with the grid note; the advisory half quotes the monitoring guidance as advice and the two dose passages under the label heading |

## 4. Measured state

| Check | Result |
| --- | --- |
| Python suite | **1,351 passing** (6 new checks in tests/test_agriculture_repairs.py; the window-rule check in tests/test_engine_refinement.py and the grammar check in tests/test_answers.py were re-pointed to the new, justified rules) |
| React suite | 59 suites, 330 checks |
| Live answers | both reported questions answer, in Gujarati and in Hindi/Hinglish respectively |
| Audit of intent | the district point is disclosed as the catalogue's own seat; the daily product is named when it answers a window beyond the hourly horizon; no dose is presented as advice |

## 5. Two more defects the checks found

**G. A Devanagari question was answered by creating a watch.** "बारिश की संभावना बताइए" ("tell me the rain
chance") was classified as a notification request, because the notify pattern listed the bare Hindi tell-me
forms (बताइए, batana, bata dena) and the Gujarati જણાવજો as watch triggers. A bare tell-me verb is a question.
The pattern now registers a watch only for keep-me-informed forms — "notify me", "keep me posted", "batate
rehna", "सूचित", "बारिश हो तो बताइए", "bata dena jab barish ho" — and ten cases in three scripts pin the
split, including the Devanagari question that was misread.

**H. A saved watch was announced inside an unrelated rainfall answer.** A recurring plan was named in any
answer that happened to mention its city, so a Marathi rainfall answer carried "you have a standing plan for
Nashik; I am watching IMD district warnings for it". A recurring plan is now mentioned only when the question
itself is about warnings or a hazard; a dated plan is still named when the answer covers its own day, which is
the case where it belongs. The one plan this session's probing created by the misread in (G) was removed from
the local plan store; the reader's own plan was left untouched.

## 5. The Farm advisories surface: why it showed nothing, and what the brief now does

The two screenshots that reported this batch show two different failures, and only one of them was in the code.

**A stale workspace process.** The page was served by a workspace started **before** these repairs, so
`/api/advisories/holdings` answered **404** (the route did not exist in that process) and the brief read failed at
the transport layer. A server restart fixed both on this machine. The surface must also survive the case, so:

- when the holdings view is not served (a 404, or any failure), the surface **falls back to the corpus read**
  (`/api/corpus?family=district_agromet`), which every build serves and which carries the same editions, and the
  panel states that the rows came from that read and that restarting the workspace serves the newer view;
- the brief's failure panel still names the endpoint and the reason, so a reader can tell a missing route from a
  dead server.

**The brief itself, measured against real editions.** Seven changes, each checked against the indexed editions:

| Defect | Repair |
| --- | --- |
| A general request (no crop) was answered with "Poultry Shed Care" or "Live Stock Advisory" while the same edition carries COTTON, PIGEON PEA, SORGHUM and BANANA sections | a general request now considers **every indexed passage of the edition** (with that disclosed), not just the six sections the word "advisory" retrieves |
| Four slots went to one kind of section | the passages are chosen **one per crop** the edition's own headings name, then the general and livestock sections, then the weather outlook last |
| A crop was read from anywhere in a paragraph, so "slaked lime" made a poultry paragraph "lime" and "such as sugarcane" made an SMS paragraph "sugarcane" | a crop section is read from its **own heading** (the crop name in the passage's opening), so a mention does not label a passage |
| The crop and stage labels on quoted passages came from the loose reader | labels use the heading crop and the stage reader, so a quoted passage is labelled with what it is a section about |
| The weather-outlook section led the advice | the outlook is ranked last, and the brief keeps its own separate forecast half |
| A crop request could serve another crop's section (pearl millet for a grapes request) | the crop lexicon now carries the common Indian crop names (pearl millet, finger millet, pigeon pea, chickpea, sorghum, castor, sesame, the vegetables and fruits), a passage naming another crop is dropped, and the requested crop must appear in the passage; when nothing matches, the brief refuses and names the crops the edition does state |
| A state edition could not be read from the surface at all (the route demanded a district) | a brief with a state and no district reads the state composite edition |

Measured after the repairs, on this machine: Surat (no crop) leads with COTTON (Flowering), then PIGEON PEA
(Vegetative), SORGHUM (Vegetative) and BANANA; Patna (no crop) leads with MAIZE (Silking); Surat with cotton
returns the cotton section and separately labels its dose line; Nashik with grapes refuses rather than serving
pearl millet, naming the crops the edition does state; Chhindwara with maize refuses from the *indexed* edition
(potato, pulses, soybean) while the live bulletin path serves its maize section.

## 6. What this does not claim

- The seat reading answers a **forecast question at the district's reference town**. It is not a district-wide
  map, not a district average, and not the reader's field; the note says so on every such answer.
- Daily rain values are the source's own 24-hour sums over its own :30-to-:30 days. They are model forecast
  values for a grid point, not observations, not a gauge reading and not a district average.
- The hourly product covers up to 48 hours and its grid runs on :30 IST; a window that starts or ends off that
  grid is served with the covered part named and the remainder stated as not covered.
- Dose text is quoted as the label it is. The workspace still does not choose, adjust or endorse a dose, a
  spray schedule or an irrigation decision, and the product label and the local advisory remain the deciders.
- Nothing here changes a source's registry status: S21, S57, S62 and S07 keep their recorded approval states
  and unresolved terms, and no source becomes operational because it answered.

## 7. Open items

1. The planner still decides the window before the tool is chosen; a window the planner expresses as a single
   instant cannot be repaired here, and the rule that reads spoken ranges covers the common phrasings only.
2. A district seat is a catalogue town, not a boundary-weighted centroid. A district-level forecast product
   (as opposed to a point reading) remains a separate, unbuilt contract.
3. The daily product for a window beyond 48 hours is the GFS summary (S21); the extended hourly product (S62)
   and the ensemble and extended-range products are not stitched together into one multi-day view.
4. Retrieval for advisory text is still lexical over the indexed editions, and the crop and stage labels come
   from the source's own words or the extractor's annotation where it exists.
