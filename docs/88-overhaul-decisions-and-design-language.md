# 88 — Decisions confirmed, the weather-native design language, and the next overhaul scope

17 September 2026. The user confirmed **all six decisions** from [docs/87](87-frontend-research-and-inspiration.md)
and added the next scope in the same message: document everything first, uplift the features that were not the
focus of the first run, then plan and build a landing page and an owner gate, all under a **weather-native design
language** — the product should *look* like WeatherGPT. No further questions; keep working, commit regularly.

## 1. The six decisions, confirmed

| Decision | Confirmed as |
| --- | --- |
| CSP | green-lit — and then made moot by measurement: R0 proved no relaxation is needed, so `script-src` and `style-src` both stay `self` (see §3) |
| Streaming | staged contract now (first reading, stages, complete answer) with a seam; SSE of the written answer is its own later batch |
| Layout | chat centre with a resizable workbench panel for modules; the existing routes stay for deep links |
| Transcript library | assistant-ui primitives (MIT, shadcn registry, RTL-ready) mapped onto our engine packet; the Radix + own-reducer path stays the documented fallback |
| Fonts | self-hosted woff2 subsets: a Latin face plus Noto Sans per script, loaded on demand |
| Baseline | Tailwind v4 + shadcn/Radix, with React Aria/S2 where Radix has no equivalent |

## 2. The design language: the interface should read like weather

The instruction is that the product should carry the *context* of WeatherGPT. That is a visual language, and it
has to be built the way the rest of this repository is built: **what is decoration says it is decoration, and what
is evidence carries its source.**

### Sky phases, driven by the one thing that is always true here

Six phases — `predawn`, `dawn`, `day`, `dusk`, `night`, `storm` — are selected from the **local clock** (a fact
this machine always has) and applied as `data-sky` on the document. Each phase publishes a contrast-checked pair
of surface and ink colours in both themes; the auditor's colour rules apply. The `storm` phase is *not* selected
automatically: it is reserved for a surface that is already stating an official warning, so a decorative gradient
can never imply one.

Rules that make this honest:

1. **Decoration is marked as decoration.** The sky background is `aria-hidden`, carries a `title`/note saying it
   shows the local time of day, and is never described as a condition.
2. **A weather glyph appears only beside evidence.** Meteocons (MIT, `@meteocons/svg`) render a condition only
   where a packet states it, with its source and time; chrome uses Lucide (ISC). No pictogram is ever used as
   ornament where a reader could take it for weather.
3. **The warning palette is reserved.** Ambers, oranges and reds in the warning ramp mean an official warning
   state and nothing else; the sky phases use blues, indigos, slates and soft dawn pinks that do not collide
   with it. A test asserts the two palettes share no token.
4. **Motion never lies about progress.** Sky transitions are cross-fades gated on `prefers-reduced-motion`;
   nothing loops continuously in a reading surface, and no animation implies that work is happening.
5. **Evidence typography.** Values, units and times are set in a tabular/mono face; the written sentence is
   serif; chrome is sans. A number therefore never looks like chrome.

### The module language

Every ported surface is a **module** with three exports, and the design language is defined once for all of them:

- `Block` — the compact in-chat form (a warning strip, a chart, a receipt table);
- `Surface` — the full form for the workbench panel and the deep-linkable route;
- `intents` — the questions it answers, which is how the conversation reaches it.

A module renders tool-owned text and values, states its own limits in the same voice as the current cards, and
never invents a value, a colour meaning or a confidence.

## 3. What R0 measured about the design language's prerequisites

- **CSP**: no relaxation needed. Radix positioning, TanStack Virtual rows and Motion transforms all applied
  under the strict policy, because React writes styles through the CSSOM at runtime. The design language can use
  gradients, transforms and animated transitions without weakening the page policy.
- **Bundle**: the initial graph is 71 KB gzip against a 312 KB budget; the sky CSS and the self-hosted fonts are
  the next things to weigh, and the budget step in `scripts/audit_react_build.py` is where they get weighed.

## 4. Uplifting what the first run did not focus on

The chat overhaul carried the conversation. The surfaces beside it are now the work, ranked by what the problem
statement rewards (the ranking follows [docs/84](84-ps-progress-and-pictures.md), where feature 4 is the weakest):

| Order | Module | Why this rank |
| --- | --- | --- |
| 1 | Warnings + what changed | PS feature 4 is the weakest journey; the dissemination backbone landed and the surface still looks like a table |
| 2 | Today / overview | the composed reading a reader opens first |
| 3 | Forecast + observations | the numeric heart, and where the evidence typography pays off |
| 4 | Published documents | the corpus is indexed and only partly reachable from chat |
| 5 | Farm advisories | the PS's farming use case, currently a text wall |
| 6 | Compare, climate, marine, verification, ensemble | specialist modules, each with a block and a surface |
| 7 | Briefcase, settings, plans/inbox | the working furniture, folded into the chat-first layout |

## 5. Landing page and owner gate (planned, built after the surface uplift)

**Landing.** A static, honest front page at the root of the workspace: what WeatherGPT is, the problem statement
it answers, what it refuses to claim (the same wording the README uses), a few real screenshots, and one action —
*Open the workspace*. It must be readable without JavaScript, carry no invented metrics, and be the same page the
repository documents. Inspiration to mine when it is built: the shadcn/ui landing-template ecosystem (MagicUI,
Aceternity, Tailwind Plus) for layout and motion patterns, with none of their marketing voice.

**Owner gate.** The workspace runs on loopback behind a per-process session token; there is no account system and
nothing is encrypted at rest. The gate is therefore planned as an **owner gate**, described as exactly that:

- a passphrase whose verifier is derived in the browser (PBKDF2-SHA-256 via WebCrypto, random salt, high
  iteration count) and stored locally; the passphrase itself is never stored and never leaves the machine;
- it gates the **interface** — a shoulder-surfing and accidental-access barrier on a shared machine — and is
  labelled *not authentication* and *not encryption*; the API keeps its token check either way;
- first run **explains what it is and what it is not before asking** for anything, and offers *skip* (the
  workspace stays open exactly as it is today), because a gate that overstates itself is worse than none;
- if hosting ever arrives, this gate is not the thing that secures it, and the document says so.

## 6. References consulted for this batch

- Meteocons / weather-icons (Bas Milius), MIT — https://github.com/basmilius/meteocons and
  https://github.com/basmilius/weather-icons, npm `@meteocons/svg`.
- Lucide icons, ISC — https://lucide.dev/icons/ (verified licence text in research/discovery/frontend-libraries-20260917).
- shadcn/ui landing templates and MagicUI-style component galleries (inspiration only) — links recorded from the
  2026 template surveys; to be read in full in R7 rather than cited as evidence now.
- a first-run passcode pattern discussion (*explain the lock before asking for it*) — recorded as a UX lesson,
  not as a security reference.
- R0 measurements: research/reviews/frontend-react-r0-20260917/ (CSP probe, live server checks).

## 7. What this document changes in the plan

[docs/86](86-react-frontend-overhaul-plan.md) keeps its stages R0–R6 and gains two: **R7 landing and owner gate**
after the surface uplift, and the design-language work distributed into R1 (sky tokens and typography), R2 (the
transcript's own voice) and R3/R4 (each module's block and surface). The gate for every stage is unchanged: a
stage lands only when its exit check passes and `verify_all.py` stays green, and the vanilla frontend keeps
serving until R6.
