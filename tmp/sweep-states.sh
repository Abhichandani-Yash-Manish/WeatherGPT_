#!/bin/sh
cd /Users/yashabhichandani/Desktop/WeatherGPT
export HOME=/Users/yashabhichandani
python3 scripts/ingest_state_agromet.py --only 'Maharashtra' 2>/dev/null | grep -v '^outcomes\|^written' | tail -2
python3 scripts/ingest_state_agromet.py --only 'Madhya Pradesh' 2>/dev/null | grep -v '^outcomes\|^written' | tail -2
python3 scripts/ingest_state_agromet.py --only 'Tamil Nadu' 2>/dev/null | grep -v '^outcomes\|^written' | tail -2
python3 scripts/ingest_state_agromet.py --only 'Telangana' 2>/dev/null | grep -v '^outcomes\|^written' | tail -2
python3 scripts/ingest_state_agromet.py --only 'West Bengal' 2>/dev/null | grep -v '^outcomes\|^written' | tail -2
python3 scripts/ingest_state_agromet.py --only 'Odisha' 2>/dev/null | grep -v '^outcomes\|^written' | tail -2
python3 scripts/ingest_state_agromet.py --only 'Bihar' 2>/dev/null | grep -v '^outcomes\|^written' | tail -2
python3 scripts/ingest_state_agromet.py --only 'Jharkhand' 2>/dev/null | grep -v '^outcomes\|^written' | tail -2
python3 scripts/ingest_state_agromet.py --only 'Punjab' 2>/dev/null | grep -v '^outcomes\|^written' | tail -2
python3 scripts/ingest_state_agromet.py --only 'Uttarakhand' 2>/dev/null | grep -v '^outcomes\|^written' | tail -2
python3 scripts/ingest_state_agromet.py --only 'Himachal Pradesh' 2>/dev/null | grep -v '^outcomes\|^written' | tail -2
python3 scripts/ingest_state_agromet.py --only 'Assam' 2>/dev/null | grep -v '^outcomes\|^written' | tail -2
python3 scripts/ingest_state_agromet.py --only 'Andhra Pradesh' 2>/dev/null | grep -v '^outcomes\|^written' | tail -2
python3 scripts/ingest_state_agromet.py --only 'Kerala' 2>/dev/null | grep -v '^outcomes\|^written' | tail -2
python3 scripts/ingest_state_agromet.py --only 'Goa' 2>/dev/null | grep -v '^outcomes\|^written' | tail -2
echo done
