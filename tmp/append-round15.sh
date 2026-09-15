set -e
cd /Users/yashabhichandani/Desktop/WeatherGPT
cat > /tmp/round15.md <<'EOF'
## Round 15 — paraphrase robustness: measured, then repaired, 38 of 38 on the development set

PS feature 2 lists paraphrase robustness (A01) as missing. This round measures it with
`scripts/measure_paraphrases.py`: eleven declared shapes and 38 deterministic wording variants (word order,
politeness, an article, Hinglish, 'kya', a misspelling, an Indic script, a station code, a coast, a compound
question, a correction), each variant holding when the planner produces the shape's declared tasks.

| | Variants | Held | Rate |
|---|---|---|---|
| Before | 34 | 25 | 0.735 |
| After the repairs | 38 | 38 | 1.000 |

Eight repairs, each a shape a reader would ask for in that wording: agromet bulletins in the document
vocabulary; a station code read as a station request with an acronym guard; Hinglish past markers for the
history shape; tide as an unconnected domain; an order-independent crosscheck shape; Indic-script questions
planned in their own language instead of refused; a native-script state disclosed as unused rather than
emptying the candidate list; and the `sea_area` kind accepted by the plan schema and validator, which had been
silently handing every coastal question to a model.

Six repaired wordings were recorded live, all planned by `deterministic_rules/rule-planner-v1`: Devanagari and
Gujarati rain questions answered (the Devanagari one rendered in Hindi through the invariant gate), a station
code answered as an airport report, the Hinglish agromet bulletin answered, the tide question answered with
the not-connected gap, and the Hinglish crosscheck answered with both sources' series.

Not established: this is a development set by construction and is not a generalisation measurement (the
sealed sets remain at 0.615 and 0.545); a plan is not an answer; no native speaker has reviewed the
Indic-script output; the variants are generated, not sampled from users.

EOF
cat /tmp/round15.md >> docs/49-engine-architecture-and-gap-analysis.md
grep -c 'Round 15' docs/49-engine-architecture-and-gap-analysis.md
