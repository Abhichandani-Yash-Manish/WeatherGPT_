# Meridian Light — design QA

22 September 2026. Target: the selected light revision, `reference-light.png` (1487 × 1058). Implementation: **the main React app on http://127.0.0.1:8765**, not the independent Vite exploration in this directory.

## Comparison and iteration

The selected image and actual app captures were viewed together in the same comparison input twice. Final desktop capture: `qa-main/answer-final.png`, 1440 × 1024. Both show a completed Surat/Vadodara comparison with the evidence margin closed. Content is deliberately the real packet rather than the reference's illustrative prose; the final screenshot is a restored real answer and carries its restoration notice. The capture and reference have slightly different aspect ratios; this is a direction/fidelity review, not a pixel-diff claim.

1. Initial integrated capture (`answer-01.png`) exposed clipped collapsed-rail actions, uneven prominence of one source's zero, excessive vertical claim stacking and a hard artwork edge. The rail now has proper icon-only controls; compatible comparisons use a dimension-checked matrix; the contour image fades radially at its edges.
2. A native scrolling anchor moved the answer as text settled. The thread now opts out of browser overflow anchoring while retaining the existing explicit newest-question anchor. Final inspected thread starts at scrollTop 0.
3. Source receipts were grouped without dropping older editions. UI inspection opened S21 and showed two separate citation receipts with their original read times and publisher links.
4. The first palette audit found the metadata ink under AA on selected-control fill. The tertiary ink was darkened; active Meridian text and hazard-wash checks pass.
5. At 360px, an offscreen rail cast a shadow into the chat. The closed drawer now has no shadow. Page width equals viewport width; composer bounds are 16–344px. Tables scroll internally with keyboard access.
6. Watch received a persistent section navigator. Browser verification opened Browser push through the navigator and returned to chat without creating or changing a subscription.

## Five fidelity surfaces

| Surface | Outcome |
| --- | --- |
| Typography | Inter interface/prose with existing script fallbacks; numeric and receipt typography remain mono. Live prose wraps naturally, so its headline is longer than the illustrative reference. |
| Spacing and geometry | Slim collapsed rail, broad reading column, answer-owned right margin on wide containers, fixed composer. Source margin moves below the answer when room is insufficient. Expanded navigation preferences are preserved. |
| Color and material | Mineral-white ground, slate ink, muted blue accents, opaque matte panels. Source-owned warning colors remain independent. FE14/FE16 include the active palette and pass. |
| Assets | Original generated contour artwork and Meridian mark are bundled locally. No runtime remote image dependency. The city illustration was removed from the welcome. |
| Content and controls | Real engine answer, comparisons and all source receipts; no reference's example data was hardcoded into production. Held place is labelled independently of places a previous answer resolved. Source catalogue citation remains visible as a third source when the packet contains it. |

## Motion and functional evidence

- Fresh live query completed through the actual conversation controller; the later check recorded 8.062 seconds of server work. This is one run, not a performance benchmark.
- Working text came from actual engine stages. The CSS has 24-second idle contour motion and an 8-second busy state; no stage is driven by a cosmetic timer.
- Browser-computed animation state was `paused` with the pause control active and `paused` while the question textarea had focus. Idle state was `running` with a 24-second duration. Reduced-motion behavior is declared in CSS; no separate browser-emulated reduced-motion session was recorded.
- The 1440px and 768px checks showed no document overflow. At 768px the answer used a single 728px column. Final 360px measurement showed scrollWidth = innerWidth = 360 and a reachable composer. These are layout checks, not mobile acceptance.
- Screenshots cover the welcome, completed answer, 768px/360px chat, warning overview and Watch navigation. `working-final.png` was taken after the fast cached request had already settled and must **not** be used as evidence of a working-state frame.

No outstanding P0/P1 layout or interaction defect was observed in these sampled flows. This does not certify every guided module or exact image fidelity. The original content, navigation and accessibility requirements intentionally take precedence over duplicating an illustrative mockup's shorter text or source count. The backend-returned Watch wording remains a documented product issue in docs/160.

## Verification

`verification/full-gate.txt`: 21 steps, zero failed, 1,630 backend tests. `verification/react-tests.txt`: final 559 checks / 85 suites passed, no unhandled errors after the copy-feedback timer repair. Production build and typecheck passed. `verification/frontend-audit.txt`: 19 checks, zero failed. The bundle-size warning remains; no frame-rate benchmark, real-device speech/push acceptance or deployment was performed.
