# Embedded PDF viewing and its accessible controls — 15 September 2026

[The gap register](31-full-solution-gap-register.md) recorded **G18** from docs/21 A08: saved PDFs downloaded with a same-origin fallback, and embedded viewing plus broader accessibility checks stayed open. This batch adds an in-place, collapsed, same-origin viewer and the component checks that pin it.

## What changed

- **Open the saved source PDF in place.** Every archived passage now offers View saved PDF here. The toggle is collapsed by default and creates the iframe only when pressed, so opening the evidence drawer does not download a large PDF nobody asked for. The frame is same-origin (/api/documents/<sha>#page=N) and never points at a publisher or third-party origin; the download link remains the fallback when the browser has no built-in viewer.
- **Accessible state.** The toggle carries aria-expanded and flips its label between View and Hide; the iframe carries a title naming the source and page; the frame host states that the browser renders it from this workspace only. The workspace Content-Security-Policy now names frame-src 'self' explicitly (frame-ancestors stays 'none', so nothing can embed the workspace itself).
- **A component check** asserts the viewer starts collapsed, no frame exists before the toggle, the frame src is same-origin and page-anchored, the title is present, aria-expanded tracks the state, and reopening hides the existing frame instead of fetching another.

**631 automated tests pass and the full verify command reports 19 steps, 0 failed.**

## What this does not establish

- **No browser or assistive-technology acceptance.** The checks run against the DOM shim; real screen-reader, keyboard-only and mobile-browser journeys are unperformed.
- **No visual/layout review** of the embedded frame across browsers, and no claim that every browser embeds PDFs; the download fallback exists exactly because some do not.
- **No accessibility audit beyond these controls.** Contrast, focus order, landmark structure and long-page behaviour are not measured here.
