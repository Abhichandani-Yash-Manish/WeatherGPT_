set -e
cd /Users/yashabhichandani/Desktop/WeatherGPT
cat > /tmp/round10.md <<'EOF'
## Round 10 — the sealed holdout: 8 of 13 on cases the engine was not tuned on

The earlier holdout had been read during development, so 17/17 and 4/4 measured regression only. This round
authored a fresh set of ten unseen cases, sealed it in the registry with a rule against tuning on it, and ran
it once.

| Measure | Value |
|---|---|
| Declared tasks completed | 8 of 13 (0.615) |
| Prohibited-claim hits | 0 |
| Critical failures | 0 |
| Tuned comparison | 17/17 development, 4/4 earlier holdout |

The five misses reduce to two root causes: two misspellings in one place name were not resolved (the engine
refused to substitute a nearby city and asked, which is honest and is still incomplete), and a coast is not a
settlement, so "warnings for the Kerala coast and waves off Kochi" stopped at a place selection offering
villages called Kerla in Rajasthan. One whole-edition read returned `partial`, and one adversarial flood case
was answered with governed modelled discharge - with no claim of an observed water level, danger level or
flood extent - against a declared status vocabulary that was authored too narrowly.

### What this changes

- The honest generalisation number for this checkout is 0.615 on unseen shapes, not 100%.
- The misses were read to write the record, so any round that fixes typo tolerance or coastal areas makes this
  set development data, and the next generalisation number needs a holdout authored after those fixes.

EOF
cat /tmp/round10.md >> docs/49-engine-architecture-and-gap-analysis.md
grep -c 'Round 10' docs/49-engine-architecture-and-gap-analysis.md
