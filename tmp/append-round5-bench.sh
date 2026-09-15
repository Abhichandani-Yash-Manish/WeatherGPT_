set -e
cd /Users/yashabhichandani/Desktop/WeatherGPT
cat >> docs/49-engine-architecture-and-gap-analysis.md <<'EOF'
- The declared acceptance benchmark was re-run after this batch with the fresh output directory
  research/reviews/acceptance-benchmark-20260915n: 17 development cases (18 declared tasks) and 4
  holdout cases answered, zero missing tasks, zero task-shape mismatches, zero prohibited claims,
  zero disallowed statuses, zero critical failures and no abstention. The holdout set has already
  been read in docs/45, so it no longer measures generalisation; the numbers above are a
  no-regression check on a set that is now development data.
EOF
grep -c 'acceptance-benchmark-20260915n' docs/49-engine-architecture-and-gap-analysis.md
