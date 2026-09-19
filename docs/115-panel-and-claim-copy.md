## 1. The panel states the place

The reading panel was three settings and a station report. It is the place's own page in miniature now: the
place, the nearest station's report, **what is published for its district**, and the hours the model returned
for it — with the answer language, the persona and the ways in under them.

![The panel: place, station, the published district days with the colours the product printed, and the next hours](../images/shell/10-reading-panel.png)

Four of the product's rules came with the two new blocks, and they are the product's rules rather than the
panel's:

1. **A quiet day is said as quiet.** A day the product flagged nothing for prints *nothing flagged* and stops
   there; it does not also print a hazard line saying the source said nothing, which is the same fact twice —
   once as a statement and once as a gap.
2. **A district with no published day is not a quiet district.** The block says the read published no day for
   this district, in those words, rather than leaving an empty list to imply calm.
3. **Every number keeps its unit and its source.** The hours are a strip, not a chart: six rows at most, each
   with the unit the payload stated, under the source id, the model and the window the read returned.
4. **A failure is the server's own sentence.** Both blocks reuse `failureSentence`, so an unavailable store
   reads as one here too.

## 2. The claim can be copied with its provenance

The claim is this product's atom — a measure, a value with its unit, a place, a window and a source — and until
now the only way to lift one into an email was to select the text on screen and hope.

![A claim with its copy action: the line is the atom's own order, measure to source](../images/shell/11-claim-copy.png)

Each claim now carries a copy action that puts **its own line** on the clipboard:

    Forecast rainfall · 0.3 mm · Ahmedabad, Gujarat · 19 Sep 2026, 18:30–21:30 IST · source S21 · forecast

Three things about it are deliberate:

- **The text is passed in, not read off the screen.** The rendered claim contains the depth panels' text as
  well — a closed `<details>` still has text in the DOM — so a copy taken from the element would include a
  receipt nobody opened, which is a different claim from the one the reader is looking at.
- **It is the atom's order and nothing else.** No headings, no prose, no confidence, no summary: measure, value
  with unit, place, window, source, kind. What is copied is what the card states, and the card states only what
  a tool returned.
- **It is dropped from a printout**, like every other control on the card, and the print-parity check now walks
  *every* marked control rather than assuming there is one.

The measure is named the way the card names it ("Forecast rainfall", the label the payload carried) rather than
the way the payload's field spells it ("precipitation"), so the line a reader pastes reads like the card they
read it from.

## 3. The place can be in the address

The panel states a place; the address can now name one. \`#/assistant?place=Kochi, Kerala&plat=9.93&plon=76.26\`
holds that place on arrival and opens the panel on it, so the place the answers are about is a link somebody can
send and a page a reader can bookmark. Choosing a place in the rail writes it into the address as well as into
this browser's storage.

It is read once per address, and a half-written one is refused rather than half-applied: a place is either a
pair of coordinates that parse as numbers and fall inside the world, or it is nothing at all.

## 4. Evidence

| Check | Result |
| --- | --- |
| `npx tsc --noEmit` | clean |
| `npx vitest run` | **62 files, 355 checks** |
| `scripts/audit_react_frontend.py` | **18 checks, 0 failed** |
| `scripts/verify_all.py` | **20 steps, 0 failed** |

Two checks fired on this batch: the **vocabulary check** refused the chip class the panel invented before the
stylesheet knew it, and the **print-parity check** refused a card that had grown a second control without the
drop being asserted on all of them.

## 5. What this does not claim

- The panel reads two governed routes per place and caches them for the session only; it is not a place page
  with its own route, and a reader cannot link to one.
- The hours strip shows six rows of what may be a 48-hour read. It is a glance, not the forecast, and it links
  to nothing yet.
- No reader other than this machine's owner has used any of this.

## 6. What is left

1. **A place's own page**, with its own address, holding what the panel now shows plus its conversations. The
   address names the place and the panel shows it; what is still missing is the page — the panel is the glance,
   and the destination does not exist yet.
2. **The panel's blocks as links**: "published for this district" should open the warnings surface at that
   district rather than leaving the reader to find it.
3. **The same copy line on the warning claim**, which is a published colour and a hazard wording rather than a
   measure and a value, and needs its own sentence rather than a re-use of this one.
