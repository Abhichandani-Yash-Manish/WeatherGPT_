# 114 — Places in the rail, a search that reaches every turn, and naming a place from the front door

19 September 2026, the third batch of the day, on [docs/113](113-shell-and-chat-surface.md) and
[docs/112](112-welcome-screen-and-sky-mark.md). The direction was open — *"focus on the rail part which you
modified and now it's better but still more progressive work can be done … maximum creativity"* — so this batch
takes the three ideas docs/113 §6 recorded first and does them properly.

## 1. Places are the second entity

A conversation is one thing this product stores; a **place** is the other, and until this batch the rail could
not tell you that a conversation had one.

![The rail's Places section: the places the stored conversations themselves resolved, each with its count](../images/shell/06-rail-places.png)

The place on a row is **the engine's own resolution**, read out of the state it wrote when it answered — not a
city name picked out of the question's words by the interface. That distinction is the whole design:

- a conversation whose answer resolved a point carries that place, with the coordinates the engine resolved;
- a conversation that resolved no point carries **no place at all**, however prominently a city appears in its
  words, and the reply omits the field rather than filling one in.

The rail lists what it knows — the reader's own pins, and the places the stored conversations resolved, with a
count — and choosing one does two things: it becomes the place this browser holds, and it narrows the list to
that place. The list is one list, not two: a pin with no conversation and a resolved place with no pin are two
different facts about a place, and neither implies the other.

**A pin and a resolution are different, and the row says which is which.** Pinning uses the store the module
surfaces already write (`pinPlace`, `unpinPlace`, `usePinnedPlaces`), so the rail and the surfaces agree about
what is pinned — a second list would have been a second truth.

This is Codex's Projects idea with the product's own entity underneath it, and it needed one honest backend
change rather than a heuristic: `Workspace.conversations` reads `resolved_points` out of the stored state
(`resolved_place`), and returns it with the row. Six checks hold it — including the one that matters most,
that a conversation about Surat which resolved nothing still carries no place.

## 2. Search reaches every stored turn

The rail's filter was a substring match on the opening question. The store has held every turn all along, so a
reader searching for what they asked about Surat could not find the conversation where Surat was the
follow-up.

![A search across the turns: the count, the place, and the turn that matched](../images/shell/09-search-every-turn.png)

`GET /api/conversations?q=` now searches the stored turns and answers with **which turn matched** — the
question or the answer — quoted. The rail shows that under the row, so a row that is there for a reason says
what the reason is, and a search that found nothing says so in words rather than showing an empty list. The
needle is trimmed, capped at 120 characters, and matched as the reader typed it: not stemmed, not expanded,
not spelled. Typing waits 260 ms before asking, because every keystroke would otherwise be a read of the store.

## 3. Naming a place from the front door

docs/112's third open item: the screen that shows your sky could not be given one.

![Naming a place: the catalogue, with the row that states no coordinates shown as one](../images/shell/08-name-a-place.png)

The welcome's place line is now the control — the held place to change it, or *Set your place* when there is
none — and it opens a native dialog over the same place catalogue the palette and the module surfaces read.
A row that states coordinates can be chosen; **a row that states none is shown as one**, disabled, with its
reason, rather than being resolved somewhere else. This closes the loop: the greeting, the station reading, the
ground's colour and every answer follow the place a reader set here, and nothing about it leaves the machine.

## 4. The keys are stated, not implied

![The key list, opened with ⌥/ or from the rail](../images/shell/07-key-list.png)

A list of the keys the shell actually answers to, opened with ⌥/ or from the rail's foot. It exists because
the shortcut hints were on the rows and the *reason* for ⌥ was only in a comment: a page cannot take ⌘1–⌘9
from the browser's tabs, so the numbering is ⌥, and the dialog says so rather than leaving a reader to wonder
why the shell is being eccentric. ⌥F opens the search and puts the cursor in it.

## 5. Two more lines, and where they came from

The corpus grew to **fourteen** with two poems from Kabir, in Rabindranath Tagore's own English of *Songs of
Kabir* (1915), both on Gutenberg (#6519) and both checked against it line by line:

- *Clouds thicken in the sky! O, listen to the deep voice of their roaring; the rain comes from the east with
  its monotonous murmur.* — poem I.71, the first rain of the season
- *The sky roars and the lightning flashes, the waves arise in my heart; the rain falls, and my heart longs
  for my Lord.* — poem LXXXVIII

Both are tagged to the monsoon months, so a January reader is not shown them. The line breaks of the printed
poems are joined into one line for the screen; the words are the edition's, and the poem number travels with
each line so anyone can check.

## 6. Evidence

| Check | Result |
| --- | --- |
| `npx tsc --noEmit` | clean |
| `npx vitest run` | **62 files, 348 checks** |
| `python3 -m pytest tests/ -q` | **1373 Python tests** (six are this batch's ledger checks) |
| `scripts/audit_react_frontend.py` | **18 checks, 0 failed** |
| `scripts/audit_port_ledger.py` | **2 checks, 0 failed** |
| `npx playwright test tests/ui/a11y.spec.ts --project=desktop-1440` | **20 passed** |
| `scripts/verify_all.py` | **20 steps, 0 failed** |

Two checks fired on this batch and both were doing their job: the **status drift guard** counted six new
Python tests and refused the README's stale number, and the **port ledger** refused a claimed test name
because the conversation-filter check had become the ledger check. Both were updated with their reasons rather
than loosened.

One defect was found by the running product rather than by a test: the new dialogs opened in the top-left
corner, because a stylesheet reset takes the browser's own `margin: auto` off a `<dialog>`. The fix is one
line and a comment, and it is the kind of thing only a screenshot finds.

## 7. What this does not claim

- **No reader other than this machine's owner has used any of this**, and the place grouping has been looked
  at on one store on one machine.
- The place labels are the geocoder's own, diacritics and all (`Surat, Sūrat, State of Gujarāt`). They are
  printed as returned rather than tidied, because a tidied label is a label no source can be held to.
- The search is a substring match over at most 200 stored conversations on a local SQLite file. It is not a
  ranking, and it will not scale to a hosted store without being replaced.
- The corpus is still English. Two Indian poems more, still no reader-language line: that remains the
  translation project docs/30 gates.

## 8. What is left, in order

1. **The quote in the reader's language**, with the translation gate docs/30 specifies. Unchanged by this
   batch and still the largest content gap on the welcome screen.
2. **A place's own page.** The rail can now group by place and filter by it, and there is nowhere to *go* for
   a place: its conversations, its station, its published warnings and its forecast are four reads that live
   on four surfaces.
3. **Renaming and merging places.** The geocoder returns `Surat, Sūrat, State of Gujarāt` and the reader may
   think of it as Surat; a conversation that resolved `Nadīād, Kheda` and one that resolved `Nadiad` are one
   place to a person and two rows to the rail.
4. **A watch from an answer** — "keep me posted about this" on a turn that named a place and a window.
5. **The whole conversation as one export**, rather than one turn at a time.
6. **Search that says how many turns matched**, and jumps to the match inside the transcript rather than
   opening the conversation at its end.
