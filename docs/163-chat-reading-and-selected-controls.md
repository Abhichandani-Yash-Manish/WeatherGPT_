# 163 — Chat reading, the welcome balance, and selected controls

23 September 2026. Continues docs/162 in the active React frontend. This is a local implementation and verification record, not aesthetic approval or full PS acceptance.

The latest user direction supersedes earlier requests for animated backgrounds: keep the existing light ground, dark rail and dark composer, remove the blinking matrix, use a static skyline, and preserve the quote between the greeting and composer. The first refinement moved the quote below the composer; the user rejected that arrangement during this session. It was restored before the final capture.

## What changed

The welcome now gives the entire skyline a visible place beneath the solar arc. It no longer hides behind controls at the bottom of the viewport. The greeting and source-owned station card share a row on desktop; the quote separates that row from the dark composer. On narrow screens they stack in the same reading order. Decorative background loops and their redundant motion button are removed. Solar position and palette still update with the actual time.

The conversation uses a bounded light reading column instead of a dark card around every answer. Claim cards retain units, geography, window, source and receipts. Evidence editions open beneath their owning answer. The question edit action is compact, response metadata remains visible, and the composer shares the answer's width. The next reply reserves enough vertical space to anchor the newest question before text arrives. The jump control sits above the composer, including when its textarea grows. Reduced motion also applies to programmatic scrolling.

The language control now uses HeroUI Select and ListBox with keyboard selection, Escape dismissal, focus restoration and a bounded portalled list. The chosen answer language survives reload. Loading and failure have explicit states, including a retry. Only languages the server marks verified for writing are offered. The place dialog restores focus, closes on Escape even from its search input, and does not mistake a click in its padding for a backdrop click. Its copy no longer claims that selected context never leaves the machine.

## A real failure behind the place button

The first live check selected **Jaipur, Yamunanagar, Haryana**, at **30.05564, 77.21282**, through the rail. The browser sent that exact home context, yet the engine searched the short name again and returned Jaipur in Rajasthan. The failing run is preserved as `live-acceptance-before-point-fix.json`; a language pass did not make its geographic result acceptable.

`held_point.py` now retains the selected coordinates when a planned settlement refers to that same selected name. It takes precedence over an older resolved namesake. A different named place, an explicitly conflicting state or district, and non-point domains still use their normal resolver. The trace records `reader_selected_point`; the point is labelled as the reader's selection, not an invented gazetteer match. Seven tests cover the failing resolver path and refusal boundaries.

The accepted live repeat kept the Haryana coordinates, rendered a Hindi narrative, then changed the same conversation to Bhopal and English. This is scoped acceptance of those UI-to-request-to-answer paths. Some evidence labels and caveats remain English, and this does not establish fluency or full multilingual acceptance.

## Verification

Evidence: [design review and screenshots](../research/design/2026-09-23-chat-refinement/design-qa.md).

- Full canonical gate: **21 steps, 0 failed**, including **1,637 Python tests**.
- React suite: **596 checks in 90 suites**. The final scroll-control and wording refinements also passed all **47 targeted checks**.
- Typecheck, production build, frontend audit and build audit passed. Initial JavaScript graph: **244 KB gzip**, within the existing **312 KB** budget; the language component loads separately.
- Shell Playwright verified welcome and answered states at **1440, 768 and 360 px**, with no horizontal page overflow.
- Axe reported no violations for the sampled welcome, language list, place dialog and restored answer. Source receipts opened successfully.
- The live language/place check recorded no browser page errors. Both the rejected and accepted geography outcomes are retained.

Standing findings: P01/P08 and R01/R10/F03 for place identity; P12/P13 and F10 for language and scoped acceptance; R11/R12/P15 for honest evidence tracking. These repairs do not close those broad findings. Forecast skill, nationwide acceptance, full translation, voice and real-device accessibility remain at their prior recorded states. The retired HTML frontend was not edited.
