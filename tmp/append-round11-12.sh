set -e
cd /Users/yashabhichandani/Desktop/WeatherGPT
cat > /tmp/round11-12.md <<'EOF'
## Round 11 — the two gaps the sealed holdout exposed, repaired

| Gap | Repaired |
|---|---|
| "Ahmedbad, Gujrat" was refused although the city matched: a misspelt state emptied the candidate list | The state resolves against the indexed names, bounded and clearly-ahead, disclosed, and never swapped for another state |
| "the Kerala coast" was searched as a settlement and offered twenty villages called Kerla in Rajasthan | A coast or sea word marks the place as a sea area; the resolver leaves it to the tools and the warning tool asks for a district or a port on that coast |
| "waves off Kochi" lost its place, and "in the Ahmedabad district" was never read | 'off' is a place preposition and an article between the preposition and the name is read |

Eight checks over the real gazetteer and rule planner, and four live journeys. The record states that the
first sealed set is now development data because its misses were read to make these repairs.

## Round 12 — a second sealed holdout, after the repairs

| Measure | Value |
|---|---|
| Declared tasks completed | 6 of 11 (0.545) |
| Prohibited-claim hits | 0 |
| Misses from a wrong product or a mis-read place | 0 (three in the first set) |
| Misses that are an absence the product states | 3 |

The number is slightly lower than the first set's 0.615, and the *kind* of miss changed: this set leans on
document, historical and aviation shapes where the corpus and connected products are thinner, and every one of
those misses is a stated absence (a Maharashtra agromet edition not held, district temperature history not held,
TAF not served). One out-of-scope tsunami question was answered as an explanation with no fabricated forecast.

Two case vocabularies have now been authored narrower than the product's honest outcome space, and that is
recorded as an authoring lesson rather than counted as an engine miss.

EOF
cat /tmp/round11-12.md >> docs/49-engine-architecture-and-gap-analysis.md
grep -c 'Round 1[12]' docs/49-engine-architecture-and-gap-analysis.md
