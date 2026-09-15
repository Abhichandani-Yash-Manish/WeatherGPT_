#!/bin/sh
set -e
cd /Users/yashabhichandani/Desktop/WeatherGPT
env HOME=/Users/yashabhichandani python3 -m pytest tests/ -q 2>&1 | tail -2
rm -rf research/reviews/acceptance-benchmark-20260915m
rm -f /tmp/bench13.log
nohup env HOME=/Users/yashabhichandani python3 scripts/benchmark_acceptance.py --set all \
  --output research/reviews/acceptance-benchmark-20260915m > /tmp/bench13.log 2>&1 &
echo "benchmark started pid $!"
sleep 12
tail -2 /tmp/bench13.log || true
