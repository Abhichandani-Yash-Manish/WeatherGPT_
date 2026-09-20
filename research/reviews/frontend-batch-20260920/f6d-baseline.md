# F6d — "the interface itself is localised (labels, dates, numerals)": what is true today

Measured 20 September 2026 while the other lanes were still running. This file exists so the localisation
lane starts from a state. Nothing here was changed by that lane; the fix has to wait for the files it has to
edit, which three other lanes hold right now.

## The row's three words, one at a time

| The criterion names | State | The evidence |
| --- | --- | --- |
| labels | **translated**, four languages | `frontend/src/i18n/{en,hi,gu,ta}.json`, `CHROME_LANGUAGES`, and `i18n.test.ts`, which holds every language to exactly the English keys, refuses a blank string, requires a catalogue for every claimed language, and refuses a unit, a source id or hazard wording inside one |
| dates | **not localised** | `frontend/src/lib/time.ts:12` is `new Intl.DateTimeFormat('en-GB', ...)` with the locale hardcoded, and lines 4 and 25 turn the month into an English abbreviation from a `MONTHS` array |
| numerals | **not localised** | `frontend/src/lib/format.ts` has no number formatting at all: `count()` concatenates a JavaScript number, so grouping and precision follow the default, not a locale |

Grep results, whole frontend, both cases:

- `Intl.` appears **once**: `lib/time.ts:12`, hardcoded `'en-GB'`.
- `toLocaleDateString` / `toLocaleTimeString` / `toLocaleString` appear **once**:
  `home/overview.ts:48`, also hardcoded `'en-GB'`.

So a reader who chooses Hindi, Gujarati or Tamil gets an interface in that language wrapped around
`18 Sep 2026, 00:30 IST`. The label above the date moves; the date does not.

## What this does not mean

**It is not a licence to machine-translate a timestamp.** The product's standing rule (docs/30) is that no
number, unit, date, place, source identifier or negation passes through a generative step unchecked. The
mechanism here is `Intl` — deterministic, and the browser's own table — never a model. Two invariants come
with it and must be held by a check, not by care:

1. **The value does not move.** A timestamp formatted for Tamil still names the same instant, and a Tamil
   rendering of a rainfall value still reads the same number with the unit the source printed. Units are
   source wording and are never translated; `mm` stays `mm`.
2. **English stays byte-identical.** `lib/time.test.ts` pins `'18 Sep 2026, 00:30 IST'` and
   `'18 Sep 2026 09:30-12:30 IST'`. Whatever the lane does, the default rendering must still produce those
   exact strings, or the product's own recorded evidence churns for a formatting refactor.

Two judgement calls the lane must argue rather than assume:

- **The zone label.** IST is a fact about the window and the engine states windows in it. `hi`, `gu` and
  `ta` locales commonly write "IST" as well, so the likely answer is that it stays — but say so, do not
  let it change silently.
- **Digits.** `Intl` with `hi-IN`, `gu-IN` and `ta-IN` uses `latn` by default, so the numerals stay
  Latin. That is the locale's own choice and consistent with values being formatted rather than translated.
  A lane that forces Devanagari digits is changing the product's appearance on evidence it does not have.

## The shape of the fix

- `lib/time.ts` takes the active locale and keeps `'en-GB'` as the default, so every existing caller that
  does not care is unchanged.
- `lib/format.ts` gains the number side (`Intl.NumberFormat`), because it is the module whose own header
  promises to state absence rather than invent a value and it currently leaves grouping to JavaScript.
- `home/overview.ts:48` loses its second hardcoded locale.
- `elapsedWords()` in `lib/time.ts` is **prose**, not a formatted value — "4 min 30 s" is words this
  interface wrote about itself, so it belongs in a catalogue key or a template the locale selects, and it is
  the one item here that is a translation rather than a format.

## What the check must be

One spec per language that renders a fixed instant and a fixed value through the interface and asserts:
the month name is the locale's; the instant and the number are unchanged; the unit is unchanged; English is
byte-identical to today. Plus a line in `i18n.test.ts`'s own spirit — that number and date output never
passes through the catalogue, because the catalogue is where a translated value would hide.

## Blocked on, not blocked by

`frontend/src/chat/parts.tsx` (lane A), the eighteen `frontend/src/modules/*Surface.tsx` (lane B) and
`frontend/src/gpt/ReadingPanel.tsx` (lane C) are the call sites, and all three are mid-edit. This lane runs
after they land. That sequencing is the reason this file is a baseline rather than a diff.
---

## What has since moved (same day, foundation only)

The formatting foundation landed while the surface lanes were still editing their files, because
`frontend/src/lib/` and `frontend/src/i18n/index.ts` were the one region nobody held.

| What | Where | What it does now |
| --- | --- | --- |
| the active locale, and the mapping from a chrome language to an Indian tag | `frontend/src/lib/locale.ts` (new) | `en -> en-IN`, `hi -> hi-IN`, `gu -> gu-IN`, `ta -> ta-IN`, and anything else falls back to the default rather than to nothing |
| the date and time formatters | `frontend/src/lib/time.ts` | take the locale from `lib/locale.ts`; the month is the locale's, and every other part is unchanged |
| numbers | `frontend/src/lib/format.ts` | `number()` formats in the locale, with `maximumFractionDigits: 20`; `count()` goes through it |
| the wiring | `frontend/src/i18n/index.ts` | the language change is also where the FORMATTING locale changes, on i18next's own `languageChanged` event, so no call site can forget it |
| the second hardcoded locale | `frontend/src/home/overview.ts` | its private month table and `toLocaleTimeString('en-GB', ...)` are gone; it reads `monthName()` and `istClock()` like everything else |

Two things were measured before they were changed, and both changed the design:

1. **Intl's short month for English is "Sept", not "Sep"** on the ICU this workspace runs. Switching the
   default rendering to Intl would have rewritten `18 Sep 2026` to `18 Sept 2026` in every recorded
   example, screenshot and spec. So the default keeps the product's own three-letter table and every other
   locale reads Intl. The day stays zero-padded, which is what the product has always printed.
2. **Intl's default `maximumFractionDigits` is 3.** Formatting `1234.5678` with no options returns
   `1,234.568` — a retrieved value rounded to fit a format. The ceiling is set from Intl's own maximum, and
   `frontend/src/lib/locale.test.ts` asserts `1,234.5678` and `0.3` survive it.

Evidence: `cd frontend && npx vitest run src/lib/locale.test.ts src/lib/time.test.ts` → **2 files, 23 tests,
all passing**, including the one that fails if the locale is ignored anywhere on the path and the one that
fails if the rounding ceiling is dropped. `npx tsc --noEmit` clean for these files. `i18n.test.ts` (12) and
`home.test.tsx` (6) still pass, which is the check that the English rendering did not move.

## What is still NOT done in F6d

- **The measurement numerals at the call sites.** `number()` exists; the surfaces that print a value still
  let React stringify it. Routing them is safe by design — grouping is the only thing that changes, and a
  retrieved value is never rounded — but every call site lives in a file another lane is holding, so it is
  the next lane's work and it needs a spec per surface.
- **`elapsedWords()`** ("4 min 30 s", "1 h 12 min") is prose this interface wrote about itself. It is a
  translation, not a format, so it belongs in a catalogue key. It is deliberately still English rather than
  half-moved.
- **`frontend/src/gpt/PlacePicker.tsx`, the rail and the module surfaces** have not been checked for an
  invented date or number of their own. Grep says the two hardcoded `'en-GB'` sites were the only ones, and
  both are now gone.
- **Nobody has looked at any of this in a browser in a non-English language.** The specs prove the strings;
  they do not prove the layout holds a Tamil month inside the space an English one occupied.

