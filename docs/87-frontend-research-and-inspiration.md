# 87 — Frontend research and inspiration, and the stack it decides

16 September 2026. The user asked for deep research across component libraries and references before the React
overhaul, with no creative or technical boundaries, and for the product philosophy to move to **chat-first**: the
conversation is the product and every other surface becomes an additive, reusable module for it. This file is the
research record and the stack decision that follows from it. It does not build anything.

## Method and evidence

Fetched and read on 16 September 2026, kept under `research/discovery/frontend-libraries-20260917/` (384 KB):

| Source | What it supplied |
| --- | --- |
| `assistant-ui-llms.txt` (80 KB, assistant-ui docs index) | chat component inventory, runtimes, shadcn registry distribution, RTL guide, markdown/tools/thread-list areas |
| `react-aria-ai-components.md` (97 KB, React Spectrum S2 docs) | Adobe first-party AI components: Prompt fields, suggestions, tokens, attachments, **Chat threads, Thread, ThreadScrollButton, loaders, ResponseStatus**, and their accessibility notes |
| `react-aria-llms.txt` + `radix-llms.txt` | the two headless primitive families, component by component |
| `shadcn-llms.txt` | 76 registry components including `chart`, `data-table`, `sidebar`, `command`, `sonner`, `resizable`, `scroll-area`, `carousel`, `direction` |
| `mantine-llms.txt` (44 KB) | the batteries-included alternative: component, hooks, charts and x-* inventory |
| `motion-llms.txt` (48 KB) | Motion (ex Framer Motion) feature areas, layout/gesture/scroll animation, reduced-motion handling |
| `tanstack-virtual-llms.txt`, TanStack Query/Table licences | virtualiser API for long threads and 72-row answers; table and server-state options |
| `maplibre-llms.txt` | MapLibre GL JS (community fork of Mapbox GL JS after the licence change), style spec, tile tooling |
| `tremor-readme.md` | 35+ Apache-2.0 dashboard components on Tailwind + Radix |
| `lucide-readme.md`, `axe-core-readme.md`, `notofonts-readme.md` | icon set (ISC), the accessibility engine (MPL-2.0, catches on average 57% of WCAG issues automatically by its own documentation), and the Noto font project |
| `ai-sdk-llms.txt` + the AI SDK documentation search API | Vercel AI SDK: provider-agnostic streaming, `useChat` hooks, "AI Elements" chat components |
| `chat-ui-libraries.md` | the 2026 landscape: assistant-ui (headless, shadcn/Tailwind, streaming, branching, attachments, tool calls), CopilotKit, Vercel AI SDK, NLUX, shadcn-chat, Deep Chat, Chatbot UI, LibreChat |
| Google Fonts CSS API probe (`Noto+Sans+Devanagari`) | per-script `unicode-range` subsets as woff2 — the self-hosting model this app needs under `font-src self` |

Also consulted by search but not read in full, so nothing is claimed from them: an eye-tracking study of four AI
chatbot citation layouts (*How Source Attribution Visualization Shapes User Attention and Preference*, MDPI 2025),
and several 2026 component-library comparison posts. The citation-layout study is flagged as a **read-before-R2**
item, not as evidence.

## Licences of the candidates (verified through the GitHub licence API unless noted)

| Package | Licence |
| --- | --- |
| shadcn/ui, Radix Primitives, Mantine, Motion, TanStack (Query/Table/Virtual), Zustand, XState, Zod, react-hook-form, react-i18next, Vite, Vitest, Testing Library, MSW, react-markdown, Recharts, assistant-ui, fontsource | MIT |
| React Spectrum S2 / React Aria (Adobe), Tremor, Vercel AI SDK, Playwright | Apache-2.0 |
| MapLibre GL JS | BSD-3-Clause (raw licence header read; GitHub reports NOASSERTION — re-verify before vendoring) |
| Lucide icons | ISC |
| axe-core (development-time scan) | MPL-2.0 |
| Noto fonts, Inter, IBM Plex | SIL OFL-1.1 |

Every candidate is permissive; nothing here forces a copyleft obligation on the served product. axe-core is
MPL-2.0 and file-level copyleft, so it stays a development dependency and is never bundled into the app.

## The stack this research decides

**Chat-first shell on a strict-CSP, self-hosted, no-runtime-CSS-in-JS base.**

- **Build**: Vite + React + TypeScript, output to `web/dist/`, content-hashed assets, served by the existing
  loopback server with the same session-token injection.
- **Styling**: Tailwind CSS v4 with a CSS-first `@theme`, seeded from the existing `tokens.css` values. Tailwind
  emits static CSS classes, which is the only kind of styling the current `style-src self` policy allows without
  weakening it, and it keeps the design tokens as the single source of truth.
- **Primitives**: shadcn/ui registry components (MIT, copied into the repo, Tailwind classes) over Radix
  Primitives, with **React Aria / React Spectrum S2** as the second family where Radix has no equivalent
  (async ComboBox for place search, DatePicker for watch windows, and the S2 AI chat primitives as a reference
  implementation of thread semantics and screen-reader behaviour).
- **Chat transcript**: **assistant-ui** as the transcript library of record — headless components distributed
  through the shadcn registry (`npx shadcn@latest add @assistant-ui/<name>`), so its source lands in our repo, it
  carries no runtime CSS-in-JS, and it ships **RTL support through logical Tailwind classes** (`ms-*`, `pe-*`,
  `text-start`, `border-s`), which is exactly what Urdu needs. Its own runtime is **not** adopted: our engine
  packet (status, facts, citations, ruler, receipt, reading line, stages) stays the contract, mapped into message
  parts. The documented fallback if its runtime model fights ours is the same component tree built from Radix
  primitives plus our reducer — decided by measurement in R2, not by preference.
- **Data and state**: TanStack Query for server state (its cache/retry semantics mirror the engine TTL model),
  Zustand for small UI state, and one explicit turn state machine (a reducer, or XState if the transcript grows
  past it) so a turn is one state machine instead of five refs.
- **Structure rendering**: react-markdown + remark-gfm with `rehype-sanitize`, raw HTML disabled, and **no Shiki**:
  Shiki and most highlighters write inline styles, which the CSP forbids. If highlighting is ever needed it is
  class-based CSS.
- **Tables and long lists**: TanStack Table + TanStack Virtual. Measured need: a marine answer can carry 72
  hourly facts, and the district and outbox tables are wide.
- **Charts**: keep `viz.js` as the measurement engine (its axes, scales and locator logic are pinned by
  `test_viz.js` / `test_charts.js`) behind a React wrapper; shadcn `chart` (Recharts, MIT) or Tremor
  (Apache-2.0) may supply *stat/KPI blocks* only if they earn their place in R4 — decided by measurement, not by
  novelty.
- **Maps**: keep the vendored basemap and the existing map module; MapLibre GL JS enters only if R4 measures a
  reason to replace the current renderer.
- **Motion**: Motion for enter/exit/layout transitions, always gated on `prefers-reduced-motion`, on top of the
  existing View Transitions usage.
- **Icons**: Lucide (ISC) as the set, bundled locally as React components (no CDN, no icon font). Material Symbols
  (Apache-2.0) only for a glyph Lucide lacks.
- **Fonts**: self-hosted woff2 subsets via `@fontsource` (MIT): a Latin face (Inter or IBM Plex Sans) plus
  **Noto Sans per script** — Devanagari, Gujarati, Bengali, Gurmukhi, Tamil, Telugu, Kannada, Malayalam, Odia,
  Arabic (Urdu, Kashmiri, Sindhi), Meetei Mayek, Ol Chiki — each loaded on demand with its own `unicode-range`
  and `font-display: swap`. This is what makes the multilingual claim real in the interface rather than in prose.
- **i18n**: react-i18next + `Intl` for dates and numbers; direction switching with logical properties and the
  assistant-ui convention above; the language selector drives `output_language` exactly as today.
- **Forms**: react-hook-form + Zod, with the Zod shapes derived from the Python contracts so the client and the
  server cannot drift apart silently.
- **Testing**: Vitest + React Testing Library + jsdom with **MSW** replacing the hand-written fetch stub; the 110
  existing checks ported one-for-one; axe-core (development-time) for the accessibility scans; the existing
  headless-Chrome CDP runner stays the browser acceptance harness so the recorded evidence format does not change.

## The chat-first module architecture

Today the frontend has 19 routed surfaces and the conversation is one of them. The overhaul inverts that:

1. **One module registry, derived from the backend.** The engine already publishes its capability catalogue
   (`/api/settings/capabilities` over `capabilities.CAPABILITIES`) and its product routes (`PRODUCT_PATHS`). The
   frontend registry is generated from those, so a new backend tool appears in the UI instead of being
   hand-wired, and a module cannot advertise a tool the engine does not serve.
2. **Every module exposes two hosts and one contract**:
   - `Block` — the compact in-chat form (a warning strip, a forecast chart, a map thumbnail, a receipt table);
   - `Surface` — the full form, for the workbench panel and for deep-linkable routes;
   - `intents` — the questions the module answers and the deep links it owns (the same strings a quick reply or a
     chip sends), which makes every module reachable *through the conversation*, not only beside it.
3. **The conversation can embed and escalate.** An answer that carries, say, a district warning renders its Block
   in the thread; one click escalates the same module to the workbench panel (resizable, keyboard-navigable)
   without losing the thread, and a deep link opens the same Surface standalone. Evidence rules do not change: a
   Block renders tool-owned text and values and states its own limits, exactly as the current cards do.
4. **The transcript is the navigation.** Starter prompts, quick replies and module intents are the primary way to
   reach a capability; the rail becomes a secondary index of modules rather than 19 parallel apps.

## What this research rules out, and why

- **Runtime CSS-in-JS** (emotion/styled-components as used by MUI and others): it injects `<style>` elements,
  which `style-src self` forbids without a nonce, and it would put the design tokens in two places.
- **Shiki / highlighter inline styles**, for the same reason.
- **A hosted chat runtime** (assistant-ui cloud, CopilotKit cloud, Vercel AI Gateway): the engine is local, the
  session is loopback-only, and conversation data must not leave the machine; only component code is adopted.
- **Browser `SpeechRecognition`**: in Chrome it delegates audio to a Google service. Voice must go through the
  existing local endpoint (Sarvam key, stated trade), not a hidden third party.
- **Full-app kits** (LibreChat, Chatbot UI): they would replace the engine contract and the evidence discipline.

## The one policy change this forces, with its exact cost

`style-src self` blocks **inline style attributes**, and every serious positioning/virtualisation/animation
library sets them (Radix/Floating UI positioning, TanStack Virtual transforms, Motion). Without a change, a
modern chat transcript cannot be built on these libraries. The option this research recommends is:

    style-src self; style-src-attr unsafe-inline

That allows style *attributes* while continuing to block injected `<style>` elements, keeping `script-src self`
untouched, and it is recorded in the frontend audit so the change is visible rather than silent. The alternative —
no inline attributes at all — would mean hand-writing positioning and virtualisation, which is the opposite of the
user instruction to use the best components available.

## Open questions for the user

1. **CSP**: approve `style-src-attr unsafe-inline` as above (scripts stay strict)?
2. **Streaming**: keep the current staged contract for this overhaul (first reading + stages + one complete
   answer), designed so a streaming transport can slot in later; or also build server-sent-event streaming of the
   written answer, which is a server change of its own?
3. **Layout**: adopt the chat centre plus a resizable workbench panel where modules open, with the existing routes
   kept for deep links; or keep full-page surfaces as the primary host and embed the chat in them?
4. **Transcript library**: adopt assistant-ui primitives (MIT, shadcn registry, RTL-ready) with our engine
   contract, and the Radix + own-reducer path as the documented fallback?
5. **Fonts**: self-host the Latin + per-script Noto subsets (a few MB in the build, no CDN), or keep system fonts
   for Latin and load Noto only where a script needs it (smaller, less consistent)?
6. **Baseline confirm**: Tailwind v4 + shadcn/Radix as the styling and primitive base, rather than Mantine
   (batteries-included) or MUI (Material 3, runtime styles)?

## What R0 does with these answers

R0 is the groundwork stage of [docs/86](86-react-frontend-overhaul-plan.md) and its exit check is unchanged:
Vite + React + TypeScript building to `web/dist/` behind a server flag, the audited bundle hash-checked against the
served bundle, the token/CSP contract re-verified (including a **measured** probe of which candidate libraries set
inline styles under the chosen policy), MSW harness in place, one route ported, and all 110 checks plus the audit
green on the React shell with the vanilla path still serving as the fallback.
