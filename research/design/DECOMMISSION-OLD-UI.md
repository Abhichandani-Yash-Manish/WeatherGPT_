# Decommissioning the instrument language

Started 18 September 2026. The instruction: ditch the old UI, remember and document what was in it, then delete
it, with no trace of the old design left in the product.

This file is the remembering. `DESIGN.md` now describes only what exists.

## What "the old UI" was, precisely

The product was designed as **a field instrument, not a dashboard** (the wording of the original `DESIGN.md`),
and later reframed as **the conversation is the product** (`docs/106`). Both framings share one visual system:

| Piece | What it was | Why it existed |
|---|---|---|
| `web/tokens.css` | The palette: cool paper, indigo accent, four IMD hazard colours, `--viz-*` chart palette, spacing/radius/motion steps | One token source the vanilla frontend and the React port both consumed |
| `web/tokens-v2.css` | The "aurora glass" layer: glass fills, aurora gradients, blur | The second-generation look, added for the React shell |
| `styles/voices.css` (the `.v3` layer) | Two typographic voices: Tiro Devanagari for prose, IBM Plex Mono for values, indigo accent, cool paper | The conversation-first reframe, scoped so it could move surface by surface |
| `landing/Landing.tsx` | The marketing page: product name, a paragraph of method, "the shape of an answer" | The first front door — a table of *words where values would go* |
| `landing/FrontDoor.tsx` | The reading-first front door: the country's today tally plus a question box | The reframe's front door; **built, tested, and never wired into the shell** |
| `shell/Aurora.tsx`, `shell/SkyBackground.tsx`, `styles/sky.css`, `shell/sky.ts` | A decorative aurora field and a clock-derived sky band behind every surface | Atmosphere for the instrument framing |
| `shell/Rail.tsx`, `shell/Topbar.tsx`, `shell/Palette.tsx` | Nineteen peer surfaces in a rail, Alt+1…9, a command palette | The architecture made navigable |
| `modules/*` (18 surfaces), `chat/*`, `plans/*`, `charts/*` | The working surfaces, styled from the tokens above | The product's capability |
| `DESIGN.md` | The written design system for all of the above | A surface could not invent a colour the system did not hold |

## Wave 1 — deleted 18 September 2026 (done)

Removed, with their tests, because nothing live imported them:

- `landing/Landing.tsx`, `landing/landing.css`, `landing/Landing.test.tsx`
- `landing/FrontDoor.tsx`, `landing/frontdoor.css`, `landing/frontdoor.test.tsx`
- `styles/voices.css` (the `.v3` layer) and its import in `styles/app.css`
- the two scans in `a11y/a11y.test.tsx` that rendered those pages, replaced by a scan of the face that is
  actually served

Verified: `npx tsc --noEmit` clean; `npx vitest run` **63 files, 353 checks, all passing** (65 files / 369
before, the difference being the deleted pages' own tests); the app builds and serves.

Kept deliberately: `landing/owner.ts` and `landing/OwnerGate.tsx`, which are live (the owner gate), and every
module surface, which still compiles against the token layer.

## Wave 2 — the palette swap (next)

The old *look* survives in one place only: `web/tokens.css` and `web/tokens-v2.css` are imported by
`styles/app.css`, and every module surface plus the shell is written against them through the Tailwind theme
(`text-ink`, `bg-glass`, `shadow-lift-*`). Deleting them today would leave eighteen surfaces unstyled.

So wave 2 repoints that theme at the new tokens — one mapping — and then deletes the old files:

1. Map the Tailwind theme onto the light layer (`--color-ink: var(--l-ink)`, `--color-ground: var(--l-ground)`, …).
2. Replace `shell/Aurora.tsx` and `shell/SkyBackground.tsx` with the computed field, or remove them outright.
3. Re-shoot every route (`node tools/capture.mjs`) and run the axe sweep; update `tests/ui/visual.spec.ts`
   snapshots, which legitimately change because the design language changed.
4. Delete `web/tokens.css`, `web/tokens-v2.css` and the `@import` lines.

After wave 2 no colour, radius, shadow or typeface from the old system is reachable, and the deletion is
structural rather than cosmetic.

## Wave 3 — the layout and the conversation interior

The old layout commitment — nineteen peer surfaces in a rail — is the philosophy's real target. Wave 3 moves
the surfaces into the conversation-first model: the transcript cards, the register switch and the
stored-conversation column (which still draws "Delete from this machine" in hazard red at content weight, the
defect `docs/106` itself recorded) are rebuilt in the light language, and the rail becomes depth rather than a
peer list.

## Wave 4 — the legacy house with a live function

`web/viz.js` and `web/sw.js` are still served and still used: the chart block draws with viz.js, and the plans
panel registers sw.js for push. They are not the old *design*; they are the old *house*. They can only go when
the charts and the notification worker are re-homed, so they are recorded here rather than deleted.

## What must not be lost with the old design

These were the good part of the old system and they are carried forward into the light language, not deleted:

1. Every value keeps its entity, window, unit, source and retrieval time.
2. Hazard colour is reachable only through a published value, and interface state never borrows it.
3. Missing, unknown, stale, quarantined and reference-only stay visible; nothing is smoothed into a value.
4. No confidence score is produced anywhere, and nothing is invented to fill a silence.
5. A surface cannot invent a colour the system does not hold — the new layer keeps that discipline by
   construction: every value in `light.css` comes from `--l-*`, which the light engine computes.
