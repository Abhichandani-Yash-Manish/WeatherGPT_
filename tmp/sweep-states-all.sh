#!/bin/sh
cd /Users/yashabhichandani/Desktop/WeatherGPT
export HOME=/Users/yashabhichandani
python3 scripts/ingest_state_agromet.py --only 'Gujarat' >/dev/null 2>&1 || true
python3 scripts/ingest_state_agromet.py --only 'Rajasthan' >/dev/null 2>&1 || true
python3 scripts/ingest_state_agromet.py --only 'Uttar Pradesh' >/dev/null 2>&1 || true
python3 scripts/ingest_state_agromet.py --only 'Karnataka' >/dev/null 2>&1 || true
python3 scripts/ingest_state_agromet.py --only 'Chhattisgarh' >/dev/null 2>&1 || true
python3 scripts/ingest_state_agromet.py --only 'Maharashtra' >/dev/null 2>&1 || true
python3 scripts/ingest_state_agromet.py --only 'Madhya Pradesh' >/dev/null 2>&1 || true
python3 scripts/ingest_state_agromet.py --only 'Tamil Nadu' >/dev/null 2>&1 || true
python3 scripts/ingest_state_agromet.py --only 'Telangana' >/dev/null 2>&1 || true
python3 scripts/ingest_state_agromet.py --only 'West Bengal' >/dev/null 2>&1 || true
python3 scripts/ingest_state_agromet.py --only 'Odisha' >/dev/null 2>&1 || true
python3 scripts/ingest_state_agromet.py --only 'Bihar' >/dev/null 2>&1 || true
python3 scripts/ingest_state_agromet.py --only 'Jharkhand' >/dev/null 2>&1 || true
python3 scripts/ingest_state_agromet.py --only 'Punjab' >/dev/null 2>&1 || true
python3 scripts/ingest_state_agromet.py --only 'Uttarakhand' >/dev/null 2>&1 || true
python3 scripts/ingest_state_agromet.py --only 'Himachal Pradesh' >/dev/null 2>&1 || true
python3 scripts/ingest_state_agromet.py --only 'Assam' >/dev/null 2>&1 || true
python3 scripts/ingest_state_agromet.py --only 'Andhra Pradesh' >/dev/null 2>&1 || true
python3 scripts/ingest_state_agromet.py --only 'Kerala' >/dev/null 2>&1 || true
python3 scripts/ingest_state_agromet.py --only 'Goa' >/dev/null 2>&1 || true
echo swept
