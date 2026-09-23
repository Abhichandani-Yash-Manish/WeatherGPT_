# Chat refinement — visual and interaction review

Scope: active React welcome, conversation, place picker and answer-language control. User references came from `/Users/yashabhichandani/Desktop/ref images` and the later attached Nadiad screenshot. Shell Playwright was explicitly requested and used. No Chrome remote or CUA session was used.

This is a directed redesign, not a pixel clone. The supplied screenshots and final rendered screenshots were inspected together. Original references include Safari chrome at 3024×1964; final desktop captures show the app at 1440×900. No pixel-fidelity percentage is claimed.

## Visual decisions

- Color: retain the existing ink `#0b0e13`, mineral light ground (time-dependent), dark composer `#151b24`, dark rail `#0c1017`, sea-green control accent and amber sun. Published warning colors retain their independent semantics.
- Type: existing Outfit interface and display family; technical numerals retain the existing numeral font. Greeting caps at 48 px; answer prose uses 18 px / 1.72, 17 px on narrow screens. Technical captions have an 11 px CSS floor.
- Space: 760 px welcome; 860 px conversation including 32 px side gutters. Skyline has its own complete footprint under the arc. No art overlaps the question input or starter controls.
- Source hierarchy: every numeric claim retains its source and time. Evidence remains expandable per source and edition. A conversational reply no longer gets a misleading retrieved-facts authorship note.
- Interaction: HeroUI owns the language list's focus, typeahead and selection behavior. The catalogue still owns place choices. The background is static; action feedback and answer reveal remain.

## Iterations and observed repairs

1. `before-welcome.png`, `before-answer.png`, `before-language.png`: captured current code before edits. The reply was a large dark container; the welcome had several intervening blocks before the composer.
2. First revision moved the quote below the composer. The user explicitly rejected that balance; the final revision restores it above the composer.
3. A percentage-width rule hid the language label. The nested select trigger now has independent sizing. The portalled menu has a 380 px / 60dvh ceiling.
4. Live selection of Jaipur in Haryana answered Rajasthan. The failed record remains; the corrected resolver's trace and coordinates are in `live-acceptance.json`.
5. The answer initially could expand to the module width because embedded chart markers matched a broad selector. Width is now scoped to the conversation container.
6. Native search input Escape could clear its text without dismissing the dialog. Escape now explicitly closes the picker and restores the initiating control.
7. The jump button overlapped the question box. It is now positioned relative to the dock, above it, so it follows textarea height.

## Final evidence

| Step | State | Result |
|---|---|---|
| 1 | Welcome with Nadiad held | Quote above composer; whole skyline visible; source-owned station reading |
| 2 | Answer-language list | Real verified languages; selection, reload persistence, keyboard and Escape checks pass |
| 3 | Place picker from rail and composer | Catalogue selections update held context; exact selected coordinates retained in accepted live reply |
| 4 | Running and answered conversation | Real stages, Hindi/English narratives, same-chat place change and newest-question anchoring checked |
| 5 | Restored answer and receipts | Original receipt notice preserved; source disclosure opens |
| 6 | 768 / 360 px welcome and answer | No page overflow; narrow layouts scroll vertically |

Screenshots: `welcome-final-{1440,768,360}.png`, `answer-final-{1440,768,360}.png`, `language-final.png`, `working-hindi-jaipur.png`, `hindi-answer.png`, and `live-answer-{1440,768,360}.png`.

`layout-acceptance.json` records zero axe violations in the four sampled states. `live-acceptance.json` records the requests' language/home fields and coordinate-preserving result without recording authentication headers. Shell scripts are `frontend/tools/check-chat-layout.mjs` and `frontend/tools/check-chat-refinement.mjs`; they return failure for recorded violations or unsuccessful checks.

Verification logs live in `verification/`. Test totals establish regression scope, not user approval, scientific accuracy or complete PS acceptance. Actual mobile devices, all keyboard/screen-reader combinations, every language and arbitrary multi-turn geography have not been accepted by this pass. Some caveats and evidence labels remain English. The user must judge the final aesthetic balance.
