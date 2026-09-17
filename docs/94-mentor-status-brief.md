# 94 — Mentor status brief: WeatherGPT (SIH26068)

17 September 2026. One document to hand over. It states what exists, what is measured, what is blocked and what
is being asked for. Nothing here is a claim of operational acceptance, and every number can be re-run from the
repository at the commit named in section 8.

## 1. In one paragraph

WeatherGPT is a local, evidence-first conversational weather workspace for India, built for problem statement
SIH26068. The language model plans every turn but supplies candidates only: it never supplies a measurement, an
entity, a window, a unit or a warning level. Those come from governed sources through connectors, and the answer
keeps entity, window, unit and source attached to every value, says what it did not read, and states unknown,
missing, stale, reference-only and cancelled states rather than filling them. The chat is the product; the
eighteen guided surfaces beside it are additive modules over the same read-model. The desktop web is the current
surface, hosting is on hold by user direction, and the product says so in its own interface.

## 2. What runs today, and how to see it in ten minutes

```sh
cd <repo> && source .venv/bin/activate
cd frontend && npm install && npm run build && cd ..
python scripts/start_weather.py        # preflight, then http://127.0.0.1:8765
```

The workspace is loopback only, behind a per-process session token, under a strict CSP. Points to try, in order:
the front door; Ask with *hello* (answered as a conversation, no source read); *Will it rain in Surat tomorrow*
morning?* (a tool-owned fact, a written sentence, a validity ruler and a receipt); *and the evening?* (continuation
keeps place, window and source); the language selector set to Hindi with *कल अहमदाबाद में बारिश होगी क्या?*;
Warnings (district-day rows keeping the colour the product printed); Published documents (printed issue date,
measured currency, saved-body state, one saved PDF); Sources and settings (the capability table, provider order,
availability and last failure); Plans and inbox (Plan Watch, push, acknowledgements).

The repeatable gate and the two suites:

```sh
python scripts/verify_all.py     # 20 steps, 0 failed on the current tree
python -m pytest tests/ -q       # 1309 tests
cd frontend && npx tsc --noEmit && npm test   # 55 suites, 296 checks
python scripts/audit_port_ledger.py           # 110 of 110 component checks named, 203 names verified
```

## 3. Status against SIH26068

| Requirement | State | The single biggest gap |
| --- | --- | --- |
| 1 Real-time weather information | partial | per-product coverage statement and a measured cold-read bound |
| 2 Natural-language querying | delivered in scope for tested shapes, partial overall | an unfamiliar request mixing two products is not independently adjudicated |
| 3 NWP integration (GFS and best-match) | delivered in scope | WRF is unconnected and is an example, not a gap in GFS |
| 4 Alerts and early-warning dissemination | partial, the weakest journey | no live changed edition has reached a real device with the acknowledgement returning |
| 5 Location-based forecasts and advisories | partial | a conditional general-section statement is not yet reconciled with the crop passage |
| 6 Indian-language support | partial, measured | no native-speaker acceptance; the interface is not localised |
| 7 Climate trends and historical analysis | partial | the district geography used is not dated by a crosswalk |
| 8 Voice for rural accessibility | path implemented, not accepted | real audio, measured spoken output, a keyboard-free journey |
| Mobile platform | not accepted | desktop is the declared surface; touch and low-bandwidth journeys are unrecorded |
| Met databases and APIs | delivered in scope, breadth partial | registration is not selection: 20 of 70 addresses are active |
| Scalable real-time ingestion | not demonstrated | no sustained run; hosting is held |

The full table, with the delta each row owes and the queue that closes it, is docs/93; the integration audit and
the definition of done per feature are docs/89.

## 4. Source position (ledger compiled 16 September 2026)

70 addresses are registered and probed; each carries a recorded status and the probe that produced it. Two facts
stay separate: **connected** means a registered connector ingests the address, and **wired to chat** means an
ordinary conversation can reach it. Registration is not selection, and a reachable address is not a validated
product. The ledger today: 20 active through a governed connector, 3 active through another registered source,
15 blocked by a credential or licence gate, 10 reachable but not connected, 5 awaiting a product address,
10 catalogues or documentation rather than data products, 4 without an address, 3 not sources; one probe failure
(S11) is kept.

Approval is recorded as *approved_local_prototype*: redistribution is not approved and production approval is not
granted.

## 5. Why the blocked sources matter, and which ones actually block journeys

All fifteen blocked rows point at `api.imd.gov.in` and return 401 without credentials. They matter for three
different reasons, and only the third category is irreplaceable.

### 5a. Authority and wording (nine rows, substitutes exist but are not the authority)

| Blocked row | Substituted today by | What the substitute is not |
| --- | --- | --- |
| S01 IMD current weather | nearest-station layers and model hours | not the authority's current-weather product |
| S02 IMD city forecast | S62 model point output | not IMD wording or IMD city identity |
| S03 IMD district nowcast | S15 WFS warning layer | the layer is IMD-defined but not the nowcast product feed |
| S04 IMD district warning | S15 WFS warning layer | structured issue/validity times and update semantics are derived, not published |
| S05 IMD city forecast mapping | basemap and geocoder | no substitute carries IMD city identifiers |
| S39 IMD AWS/ARG station data | S63 station layer | the layer's AWS time field is a 1970 placeholder, so instants come from other fields |
| S40 IMD station mapping | S63 layer | station identity and coordinates depend on the layer, not the authority's mapping |
| S42 IMD basin QPF | S63 basin layer | day fields are verbatim but the product feed is not read |
| S43 IMD cyclone track | S63 cyclone layer | layer geometry, not the authority's track product with its own metadata |

### 5b. No substitute at all (five rows, and these are the ones that keep journeys closed)

| Blocked row | What it would open | What stays closed without it |
| --- | --- | --- |
| S41 IMD district rainfall monitoring | rainfall departures and district rainfall monitoring | recorded in the ledger as *the largest single gap on the agriculture and flood journeys*: advisory and flood reasoning stays partial (features 1 and 5) |
| S44 IMD cyclone wind warning polygons | the cyclone warning area | no cyclone warning area can be shown or matched to a place (feature 4) |
| S45 IMD cyclone cone of uncertainty | the published uncertainty geometry | no forecast-track uncertainty can be shown (features 1 and 4) |
| S52 IMD port warning | official port warnings | marine warning text has no official structured supply (feature 4, marine) |
| S53 and S54 IMD sea-area and coastal bulletins | official sea-area and coastal warning products | their document routes (S58, S59) are recorded reachable but not connected to the intake sweep, so official marine warnings remain unclaimed |

### 5c. Provenance, and the precondition for ever claiming authoritative warnings

Today the product refuses warning dissemination, and that refusal is a design line, not a bug: a resolved CAP
reference or a matching district colour never authorises dissemination (docs/71, docs/85). A credentialled
official channel with published issue and validity times is a **precondition** for any future claim that a
warning came from the authority. One caveat matters for honest reporting: an API key authenticates the *channel*,
not the content. It would remove a workaround and give structured metadata, but dissemination would still need a
published or signed path before any claim of origin authentication.

## 6. The specific asks

1. **An IMD API key for `api.imd.gov.in`**, or a written statement that it cannot be granted for a student
   prototype. Either answer closes the row in the ledger instead of leaving it blocked.
2. **If a key is not possible**, documented permission to treat the public WFS and document routes as the official
   supply, so those answers can be labelled official rather than alternative.
3. **Reviewers and testers**: native speakers per script for feature 6, a warning-domain reviewer for the
   dissemination wording, and a field tester with a real device and real audio for features 4 and 8.
4. **A scope decision on mobile**: the desktop web is the current surface and hosting is held; whether mobile
   acceptance is pursued this cycle is a user and mentor decision, not an engineering one.
5. **A licensing confirmation**: the recorded approval is local prototype use only, with redistribution not
   approved. SIH context for that limit should be confirmed in writing.

## 7. What is not claimed, and what would falsify the claims

Not claimed: operational acceptance, validated forecast skill, nationwide corpus acceptance, live warning
dissemination, origin authentication, native-speaker language quality, real-audio or field voice acceptance,
mobile acceptance, service-scale operation, and any confidence, risk or skill score. A passing gate is regression
coverage, not correctness.

Falsifiable by: a mixed-product request answered with one product and no refusal; a document pair that contradicts
itself across a general and a crop section; a real device journey where the notification or the acknowledgement
fails; a language rendering that breaks the deterministic value check; a cold read that exceeds its stated bound;
a district whose warning colour is read from anything other than the source product.

## 8. The next steps, and how to verify this brief

The ordered queue is in docs/93: Q1 whole-document recall and contradiction handling in the corpus chat path;
Q2 the live Feature 4 device journey; Q3 the feature 5 contradiction in a real document; Q4 coverage and the
cold-read bound; Q5 independent adjudication; Q6 native-speaker review and interface localisation; Q7 real audio;
Q8 the dated district crosswalk; Q9 the three engine repairs; Q10 mobile, service scale and operations. Q1 is the
highest-value item and gates Q3.

Evidence behind this brief: the gate run, the two suites, the four audit outputs, the source-ledger counts and the
corpus figures read by the served documents page are recorded in
`research/reviews/ps-closure-review-20260917/` (README, gate.txt, python-tests.txt, react-suite.txt, audits.txt,
counts.json); the registry copies are `data/registry/source-review.json`, `product-progress.json` and
`hardening-progress.json`; the picture set is regenerated from the served React build into `docs/images/`.
