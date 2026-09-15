set -e
cd /Users/yashabhichandani/Desktop/WeatherGPT
cat > /tmp/round16.md <<'EOF'
## Round 16 — state agromet coverage: one edition became five, and a marker bug

The first sealed holdout's coverage miss was a state agromet edition the corpus did not hold. This round built
a 22-centre target registry from the publisher's own `<centre>/mcdata/agromet.pdf` pattern, added a per-state
ingest path with the district outcome vocabulary, and swept every target.

| Outcome | Target count |
|---|---|
| Ingested with their printed issue dates | 5: Gujarat, Rajasthan, Uttar Pradesh, Chhattisgarh, Karnataka |
| HTTP 404 at the centre address | 16 |
| Provider cooldown | 1 |

The corpus went from 1 state edition and 257 passages to 5 editions and 890 passages. Karnataka states no
printed issue date, recorded as `printed_issue_not_stated`; the two Devanagari editions' printed dates differ
from the retrieval date and are recorded as such.

**The defect this found.** `_squash()` collapsed text to `[a-z0-9]` before comparing a title against the
family markers, so a Devanagari title squashed to the empty string - and the empty string is a substring of
every document. Adding an Indian-language marker would therefore have made the family accept any PDF as a
state agromet bulletin. It is fixed to keep letters and digits in any script, pinned by three checks including
one that refuses an unrelated bulletin. Two consequences were corrected with their evidence recorded: the
edition language now follows the script of the title that matched (two relabels recorded), and the family
accepts any of its sampled titles (`markers_any`) as the district family already did.

Not established: nationwide state coverage (centres publishing elsewhere are unknown), and a 404 at a guessed
address is not evidence that a state has no bulletin. No agronomist or native speaker has reviewed the
Devanagari editions.

EOF
cat /tmp/round16.md >> docs/49-engine-architecture-and-gap-analysis.md
grep -c 'Round 16' docs/49-engine-architecture-and-gap-analysis.md
