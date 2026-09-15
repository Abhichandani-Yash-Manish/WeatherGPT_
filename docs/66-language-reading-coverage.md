# Reading the question in every language we can write — 15 September 2026

The workspace could write answers in 21 Indian scripts and could not read a day, a part of day, a
measure or a place name in most of them. A Hindi question about tomorrow morning took 12.6 s through
a model and came back with a different morning window than the identical English question; a Gujarati
question about tomorrow read no day word at all and asked for a date; Urdu, Marathi, Assamese, Sindhi,
Nepali and Odia rain questions had no rules plan and two of the scripts had no place extraction. This
batch makes the reading side match the writing side, and records the languages it still cannot read.

## What was measured before

Eight questions, one per language, through the real engine:

| Question | Before |
|---|---|
| `કલ અમદાવાદ, ગુજરાતમાં વરસાદ પડશે?` (Gujarati, tomorrow) | read no day word — the table held only the formal આવતીકાલે — and asked for a date |
| `कल सुबह वडोदरा, गुजरात में मौसम कैसा रहेगा?` (Hindi, tomorrow morning *and* general weather) | 12.6 s through a model, planned **06:30–12:30** where the English form planned 09:30–12:30, because `dialogue.ground_relative_slots` held its own morning band |
| `آج شام دلی میں بارش ہوگی؟` (Urdu, today evening, rain) | no plan: the rain words held no Urdu, and the model that was asked failed validation — `Question interpretation did not preserve the requested tasks` |
| Marathi उद्या सकाळी पुण्यात पाऊस पडेल का?, Assamese বৰষুণ, Sindhi مينهن, Nepali वर्षा, Odia ବର୍ଷା | no plan: none of those words was in the measure tables |
| `কাল সকালে কলকাতায় বৃষ্টি হবে?` (Bengali), `ਅੰਮ੍ਰਿਤਸਰ ਵਿੱਚ` (Punjabi), `دلی میں` (Urdu), `ଭୁବନେଶ୍ୱରରେ` (Odia), `ನಲ್ಲಿ` (Kannada) | no place read at all, so a question that named its own city was answered by asking which city was meant: Bengali, Gurmukhi, Odia and the Arabic script were missing from the place character class, and the marker list held only the forms four languages use |

Two of those were defects in the *engine's own* tables rather than coverage: a part of day with no day
word read no window at all ("Will it rain in the morning?" asked for a date), and there were two
definitions of the morning window in the codebase.

## What changed

**One table per language, and one definition per part of day.** `rule_planner.TIME_WORDS` holds the
day and part-of-day words per language; `PART_WINDOWS` holds the four parts as IST windows and every
language shares them. `dialogue.ground_relative_slots` no longer carries its own bands (morning was
06:00–12:00 there and 09:30–12:30 in the rules floor) — it reads the same tables, so a model-planned
Hindi turn and a rules-planned English one settle the same hours. `language.settle_time_window`
additionally settles a window a model wrote: a question that names its own day or clock times wins,
and a question that names neither is left as planned so a continuation keeps the day the conversation
already established.

**A part of day with no day word is the coming one.** "Will it rain in the morning?" now reads today's
morning window, or tomorrow's once that window has already begun, and says so in the assumption. Before
it read no window and the turn asked for a date and an hour.

**Measure words, per language, with an audit.** `MEASURE_WORDS` holds rain, temperature, humidity and
wind words per language; the four core measures are required for every language that is not declared
unread, and `scripts`-level checks assert each word can match itself whole and resolves to its own
measure. Urdu بارش, Marathi पाऊस, Assamese বৰষুণ, Sindhi مينهن, Odia ବର୍ଷା and Nepali वर्षा now plan
through the rules floor. The four extras (probability, apparent temperature, gusts, visibility) are
held in the languages they were measured in and are not claimed elsewhere.

**A general weather question is answered without a model.** `मौसम`, `હવામાન`, `வானிலை`,
`ಹವಾಮಾನ`, `వాతావరణం`, `കാലാവസ്ഥ`, `আবহাওয়া`, `ପାଣିପାଗ`, `ਮੌਸਮ`, `موسم`, `हवामान` and
`weather` read as the four parameters the planner prompt already names for general weather, so
"कल सुबह वडोदरा में मौसम कैसा रहेगा?" plans in 0.02 s instead of waiting on a model. The missing place
is asked for, never invented.

**Every script's locative marker, longest first.** The place character class now covers Bengali,
Gurmukhi, Odia and the Arabic script; the markers are per language and split into attached
(`পুৰণি`-`ত`, `-ରେ`, `-میں`, `-۾`, `-यിൽ`) and separated (`वडोदरा में`, `ਅੰਮ੍ਰਿਤਸਰ ਵਿੱਚ`)
forms, and are tried longest first: with a single greedy pattern Malayalam `കൊച്ചിയിൽ` was read as
`കൊച്ചിയ` with the short `ിൽ` instead of `കൊച്ചി` with `യിൽ`, and Tamil `அகமதாபாத்தில்` as
`அகமதாபாத்தி` with `ல்`. A zero-width joiner or non-joiner between a name and its marker is typing,
not spelling, and is tolerated.

**The marker table is written as escapes.** While writing the Odia locative the Gurmukhi lookalikes
`ਰ`+`ੇ` (U+0A30 U+0A47) were entered where `ର`+`େ` (U+0B30 U+0B47) belongs, and Odia read no place
at all. The table is now stored as `\uXXXX` escapes generated from the module's own code points, and a
check refuses a marker whose characters span two scripts.

## Measured after

Eight questions, one per language, recorded in
\`research/implementation/language-time-reads-20260915/journeys.json\`. Three runs of the same eight
questions through the same engine:

| | Run 1: before any of this | Run 2: day words only | Run 3: after this batch |
|---|---|---|---|
| Answered | 7 | 3 | 6 |
| Planned with the product's own window | 4 of 8 (the rest: the model's 06:30-12:30 morning) | 8 of 8 | 8 of 8 |
| Planned by a model (12 s and up) | 5 | 0 | 2 |
| Raised an exception | 1 (Urdu) | 0 | 0 |
| Slowest question | 18.7 s | 1.2 s | 4.3 s |

Run 1 answered more questions and read the wrong window in half of them, through a model that made the
same question mean different hours in different languages. Run 2 read every window from its own words
and could not place any of the six non-Latin scripts, so it asked which city was meant. Run 3 reads the
window from the question and the place from the question in eight of ten scripts, and the two that still
ask are the ones whose locative changes the stem.

Reading coverage, counted from the tables the planner uses:

| | Before | After |
|---|---|---|
| Languages with any day or part-of-day word | 10 of 23 | 18 of 23; 5 declared unread by name |
| Languages with all four core measure words | 8 of 23 | 18 of 23; the same 5 declared unread |
| Scripts the place class covers | 6 | 10 |
| Locative markers held | 11 forms | 40 forms, attached and separated, longest first |

The two questions that still ask are Marathi and Tamil, whose locative changes the stem
(`पुण्यात` for `पुणे`, `அகமதாபாத்தில்` for `அகமதாபாத்`): the extracted name is a stem the catalogue may
not hold, so the engine asks for confirmation instead of answering for a place nobody named. That limit
is pinned by a test rather than described as success.

The declared acceptance benchmark was re-run: **18 of 18 declared tasks (1.0)** on the development set,
after D08 — the Gujarati "will it rain tomorrow?" case — was the failing turn while the Gujarati day
word was missing. The holdout stays at 4/4 in the runs recorded beside it.

## What this does not establish

- Reading a language is not writing one. The language registry's measured speak, write and hear
  directions are unchanged by this batch; a question can now be read here and still have no measured
  answer rendering.
- No native speaker reviewed any of this vocabulary, and no fluent, grammatical or idiomatic review of
  any Indian-language answer has taken place. The words are the everyday ones; that is a claim about a
  table, not about a reviewer.
- Bodo, Kashmiri, Maithili, Manipuri and Santali are declared unread for day words and measures: no word
  this workspace can stand behind is held for them, and a guessed day word would answer for the wrong
  day. Their questions keep the model-reading path.
- Marathi and Tamil inflected place names are read as a stem and confirmed by asking.
- One process, one machine, one instant against live sources; no load, device or browser measurement
  follows from these numbers.
