# 113 — One rail, a reading panel, a line for the hour, and the legacy tree

19 September 2026, the second batch of the day. The user's direction: *"the chat history is not collapsible or
customisable or something, the rail seems like a half-hearted component and the chat section also micro
adjustments could be done … take inspiration from the latest Codex layout … do the quotes part, handle it
yourself, it should be very classy and creative … delete and wipe out the legacy html code but before that
make sure that it is unused … keep doing regular commits, document, update and integrate everything nicely."*

It sits on [docs/112](112-welcome-screen-and-sky-mark.md), which is the welcome screen and the ground, and on
[docs/111](111-mature-design-system.md), which is the design system. Three commits carry it: the welcome and
the quote, the shell, and the legacy removal.

## 1. The rail, rebuilt

There were two columns of navigation standing side by side — a 56px strip of four homes and a 264px list of
conversations, 320px of a 1440px window to say what one column says better. The shape is Codex's sidebar:

| | |
| --- | --- |
| ![Ask at 1440: the rail with its homes, the place, the conversations, and the welcome](../images/shell/01-ask-welcome.png) | ![The reading panel open: the place, the station report, the language and the persona](../images/shell/02-reading-panel.png) |
| **The rail.** Brand row with its controls, the four homes as a block, the place the answers are about, then the conversations — the reader's own pinned ones above the recency groups. | **The panel.** The three things an answer depends on, which used to be two native selects in the top bar. |
| ![The rail collapsed to its icons](../images/shell/03-rail-collapsed.png) | ![A phone: the rail is a drawer, the page keeps the screen](../images/shell/04-phone.png) |
| **Collapsed**, and the arrangement is remembered in this browser. | **A phone.** The rail is a drawer and the page keeps the whole screen; the bar names the thread. |

Four things it now does that it did not:

1. **It collapses**, with a control, a state that survives the visit, and a key.
2. **It is the navigation**: the four homes are a block at its top rather than a second strip beside it.
3. **It states the place**, with a way to change it (the palette, which is the product's one place search) and
   a way to ask about it.
4. **Rows are arrangements and deletions**: a pin remembers a conversation in this browser and never touches
   the store; a delete names the conversation, asks first, and is a real deletion of local evidence.

**The keys are ⌥, and that is a decision rather than a style.** A browser owns ⌘1–⌘9 for its tabs and ⌘B for
bold; a page cannot take them, and printing a shortcut that does not fire is worse than printing none. The
rail prints ⌥N and ⌥1–⌥9 beside the rows they open. They are read from `event.code` rather than `event.key`
because ⌥B arrives as "∫" on macOS — a handler written against the letter works everywhere except the machine
this product was built on, and the check fires the codes a browser actually sends.

**The bar** names the thread (a conversation has only ever had one name — the question it opened with) and it
is the page's h1 only once a conversation exists, because on the welcome the greeting is the heading and two
h1s is a structure a screen reader has to guess at. A press back to the newest turn appears once the thread is
scrolled.

## 2. A line for the hour

![The line under the reading: a short rule, the verse, and the source in the mono face](../images/shell/01-ask-welcome.png)

One short line of verse under whatever the sky has said, chosen by the hour the ground is in and the month the
reader is in, and turned by a reader who wants another one.

**Every line was checked against a named edition before it was written down**, and the basis travels with it —
the two Tagore collections, Blake and Dickinson from Project Gutenberg, Rossetti from the Academy of American
Poets, Shelley from his collected poems, and Kalidasa in Arthur W. Ryder's 1912 translation, also from
Gutenberg. A quotation remembered rather than checked is an invented value, which is the one thing this
product does not print. Every line is public domain in the edition named, and the title attribute says which
edition the wording came from, so the check can be repeated rather than trusted.

Nothing is machine-translated: a line in a language the product cannot write honestly would be exactly the
claim docs/30 exists to refuse. The corpus is English, which is the language this screen already speaks, and
offering it per-reader-language is a recorded open item.

The line is not a weather statement either. A verse about rain is printed on a clear afternoon too, which is
why most lines are tagged to a time of day or a season rather than to what the sky is doing, and a January
reader is never shown "the rainy July" — that check exists.

## 3. Removing the legacy tree was a port

Eleven modules were unreachable from the entry point and are deleted: the six chat components of the
superseded Ask surface, NationalReading, the flagship solar engine, and the shell's own sky, theme and
wide-screen helpers. `src/shell/HomeRail.tsx` went with them when the rail absorbed the homes.

**What is *not* legacy was measured before anything was removed.** `web/tokens.css` and `web/tokens-v2.css`
are still imported by `styles/app.css` and still carry **73 and 20 variables the module surfaces read** —
`web/viz.js` is served at /viz.js and `web/sw.js` at /sw.js. All five stay, and the reason is in the ledger.

Then the checks started failing, and every failure was a real thing the old surface did that the shell which
replaced it had never re-connected:

| What stopped working | Why it mattered |
| --- | --- |
| The provisional first reading and the stage list under a working turn | The shell showed one line where the machine could say which stage it is on, which stages it passed, what the engine's first reading is, and how long it has been |
| The sentence naming the state a failed read leaves the reader in | An expired session and an unavailable store call for different actions, and a generic failure sentence leaves the reader guessing which happened |
| "Collect fresh evidence" | The card drew the control only when a handler was passed, and the shell passed none — the feature existed in the component and **nowhere in the product**, while FE02's check read the component and passed |
| The recogniser's own report about its hearing | The language it heard and its confidence, labelled as recognition only, which docs/30 requires |

The last one hid a defect the ported check then caught: **the composer read `result.text` and the route
answers `transcript`**, so every recording that transcribed perfectly was reported to the reader as "did not
transcribe into any text" — a sentence about the product's own failure, invented by the interface. The voice
path in the shipped shell had never worked.

The specs were re-pointed rather than dropped: a harness renders the real shell (`src/test/ask.tsx`), the two
rail checks moved to the rail's own spec, the voice checks drive the shipping composer, the accessibility scan
now runs against the surface that ships, and `home/overview.ts` is live again — the Today surface reads it
instead of keeping a second definition of the same payload.

## 4. Evidence

| Check | Result |
| --- | --- |
| `npx tsc --noEmit` | clean |
| `npx vitest run` | **62 files, 346 checks** |
| `scripts/audit_react_frontend.py` | **18 checks, 0 failed** |
| `scripts/audit_port_ledger.py` | **2 checks, 0 failed** — 199 names across 33 spec files; three checks moved with the rail that drives them and the ledger was repointed, not loosened |
| `npx playwright test tests/ui/routes.spec.ts` | **76 passed** — every registered route at four widths, no failed request |
| `npx playwright test tests/ui/a11y.spec.ts` | **80 passed** — axe including colour-contrast, at four widths |
| `scripts/verify_all.py` | **20 steps, 0 failed** |

Two checks were repaired at the cause: **FE05** followed the language control into the reading panel rather
than reading one file by name (a control that moves should not read as a control that vanished), and **FE13**
caught eight class names the ported working turn and heard panel used before either had a rule.

## 5. What this does not claim

- **No reader other than this machine's owner has used any of this.** A capture is one render on one machine.
- The quote corpus is small on purpose — twelve lines — and it is **English only**. Per-language lines are a
  translation project behind docs/30, not a copy change.
- The shell is **one implementation of a three-surface product**, tested against the routes and the axe rules.
  It has not been through a usability session, and no metrics exist.
- `web/dist-probe`, `probe.html` and the CSP probe entry are development surfaces and stay; they are not part
  of the served product and the build audit refuses them from the manifest.

## 6. Where the frontend goes next — the idea list, recorded rather than implied

Ordered by what it would change for a reader, not by effort:

1. **The quote in the reader's own language.** Twelve English lines are a start; the same lines need a
   translator, a licence and the deterministic value gate docs/30 specifies before a Hindi reader sees one.
2. **A place the reader can set from the welcome.** The rail can set it, the panel can change it, and nothing
   on the front door itself does — the screen that shows the sky cannot yet be given one directly.
3. **Conversations grouped by place.** The ledger carries the opening question and the turn count, not the
   place, so grouping them needs one field on the store. It is the Codex "Projects" idea and the most useful
   thing left in the rail.
4. **Search across stored turns**, not just their opening questions. The filter is a substring match on one
   field; the store already holds every turn.
5. **The answer's own actions on the claim**, rather than one action row under the whole turn: copy this value
   with its source line, chart this series, open this source row.
6. **A watch that can be created from an answer** — "Notify me if it rains in Pune" is an intent the engine
   already plans for, and this surface has no control for it.
7. **The print path for the whole conversation**, not one turn: a reader exporting an exchange has to print
   each card.
8. **A first-run path.** A reader arriving with no place, no conversation and no store gets the front door and
   nothing else; a single question is the only way in.
