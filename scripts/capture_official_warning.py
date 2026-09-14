#!/usr/bin/env python3
"""Capture the official warning applicability evidence.

Records, from the live official sources: the district-warning level semantics as
validated against the source's own hazard codes, the resolved day windows, two
real place journeys through the conversation API, and the corrupt-feed finding.
"""
import json, re, sys, time, urllib.request, urllib.parse, socket
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'research/reviews/official-warning-20260914'
BASE = 'https://reactjs.imd.gov.in/geoserver/wfs'
socket.setdefaulttimeout(90)


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'WeatherGPT research', 'Accept': 'application/json'})
    with urllib.request.urlopen(request) as response:
        return response.read().decode('utf-8', 'replace')


def features():
    query = {'service': 'WFS', 'version': '2.0.0', 'request': 'GetFeature', 'typeName': 'imd:district_warnings_india',
             'outputFormat': 'application/json', 'srsName': 'EPSG:4326'}
    return json.loads(fetch(BASE + '?' + urllib.parse.urlencode(query)))['features']


HAZARDS = {1:'No warning in this product',2:'Heavy rain',3:'Heavy snow',4:'Thunderstorm/lightning/squall',5:'Hailstorm',
           6:'Dust storm',7:'Dust-raising winds',8:'Strong surface winds',9:'Heat wave',10:'Hot day',11:'Warm night',
           12:'Cold wave',13:'Cold day',14:'Ground frost',15:'Fog',16:'Very heavy rain',17:'Extremely heavy rain'}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = features()
    per_colour = {}
    for feature in rows:
        properties = feature['properties']
        for day in range(1, 6):
            raw = str(properties.get('Day_%d' % day) or '')
            codes = [int(token) for token in raw.split(',') if token.strip().isdigit()]
            colour = properties.get('Day%d_Color' % day)
            bucket = per_colour.setdefault(str(colour), {})
            key = max(codes) if codes else None
            bucket[key] = bucket.get(key, 0) + 1
    validation = []
    for colour in sorted(per_colour):
        histogram = per_colour[colour]
        total = sum(histogram.values())
        validation.append({'colour_code': colour, 'observations': total,
                           'hazard_codes_present': {str(k): v for k, v in sorted(histogram.items(), key=lambda x: str(x[0]))}})

    base = 'http://127.0.0.1:8765'
    page = urllib.request.urlopen(base + '/').read().decode()
    token = re.search(r'name="workspace-token" content="([^"]+)"', page).group(1)
    journeys = []
    for question in ['Is there any official flood warning for Patna right now?',
                     'Is there an official weather warning for Ahmedabad today?',
                     'Is there an official warning for the Arabian Sea?']:
        body = json.dumps({'question': question}).encode()
        request = urllib.request.Request(base + '/api/chat', data=body,
                                        headers={'Content-Type': 'application/json',
                                                 'X-WeatherGPT-Token': token, 'Origin': base})
        began = time.time()
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                packet = json.loads(response.read().decode())
        except Exception as exc:
            journeys.append({'question': question, 'error': type(exc).__name__ + ': ' + str(exc)[:120]})
            continue
        evidence = (packet.get('warning_evidence') or [{}])[0]
        journeys.append({'question': question, 'status': packet['status'], 'elapsed_s': round(time.time() - began, 1),
                         'answer': packet['answer'], 'fact_count': len(packet['facts']),
                         'districts': [{'district': d.get('district'), 'place': d.get('place'),
                                        'issued_at_utc': d.get('issued_at_utc'),
                                        'days': [{'day': row['day'], 'date': row['date_local'], 'colour': row['colour'],
                                                  'quiet': row['quiet'], 'hazards': row['hazards'],
                                                  'starts_utc': row['starts_utc'], 'ends_utc': row['ends_utc']}
                                                 for row in d.get('days', [])]} for d in evidence.get('district_warnings', [])],
                         'stale_districts': evidence.get('stale_districts'),
                         'points_outside_districts': evidence.get('points_outside_districts'),
                         'places_without_a_point': evidence.get('places_without_a_point'),
                         'choices': [c.get('label') for c in packet.get('choices', [])],
                         'cap_messages': len(evidence.get('records') or [])})

    record = {
        'schema_version': 'official-warning-evidence-v1',
        'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
        'sources': {'district_warnings': 'imd:district_warnings_india via reactjs.imd.gov.in/geoserver/wfs (registry S15)',
                    'cap_relay': 'cap-sources.s3.amazonaws.com/in-imd-en (registry S06)'},
        'level_semantics': {
            'finding': 'Day_1..Day_5 are comma-separated hazard code lists, not severity levels. Day*_Color is an internal '
                       'WMS style parameter, not the public colour code.',
            'source_of_truth': 'The IMD district warning page own script reads warnings_arr = nc["Day_" + day].split(",") and '
                               'maps codes through its category table.',
            'official_names': {str(k): v for k, v in HAZARDS.items()},
            'validated_colour_mapping': validation,
            'public_legend_terms_on_the_imd_page': ['No Warning', 'Watch', 'Alert', 'Warning'],
            'conclusion': 'A colour may be stated because it is monotone with the hazard tier in the data itself; the four '
                          'public legend terms are rendered server-side by WMS and are not carried in the WFS attributes, so '
                          'they are not claimed.'
        },
        'day_boundaries': {
            'derivation': 'Day n is the nth IST calendar day counted from the bulletin Date field, matching the day selector on '
                          'the IMD page. IMD publishes no per-day validity field in this product.',
            'previous_state': 'adapters.warnings emitted valid_start_utc = None and temporal_applicability = "unresolved_day_boundaries"',
            'current_state': 'windows derived in IST, temporal_applicability = "day_anchored_on_bulletin_date"'
        },
        'corrupt_feed_finding': {
            'feed': 'in-ndma-en (https://cap-sources.s3.amazonaws.com/in-ndma-en/rss.xml)',
            'observed': 'Six items titled "Flood warning for Musanze Northern Province, Rwanda", authored by Meteo Rwanda, '
                        'dated 2013 and 2015, with a channel pubDate of 2018-12-06.',
            'action': 'Quarantined. It must never be ingested as an Indian official alert source.'
        },
        'journeys': journeys,
        'limitations': [
            'One machine, one local model, one clock. These are recorded journeys, not a benchmark and not unseen holdouts.',
            'Origin authentication of either source is not established; transport provenance is not sender authenticity.',
            'CAP geographic applicability to a resolved place is still not computed; CAP is reported as a source assessment.',
            'No live update, cancel or supersede example has been observed for the district warning layer.',
            'Terms are unresolved: S06 carries usage_terms "Not established for production redistribution" and every source is user_review pending.',
            'A quiet day is not an all-clear, and this work does not establish that.'
        ]
    }
    path = OUT / 'journey.json'
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + chr(10), encoding='utf-8')
    print('wrote', path.relative_to(ROOT))
    for journey in journeys:
        print(' ', journey.get('status'), '|', journey.get('question', '')[:52], '| facts', journey.get('fact_count'), '| cap', journey.get('cap_messages'))


if __name__ == '__main__':
    main()
