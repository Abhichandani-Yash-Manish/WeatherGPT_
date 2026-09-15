#!/usr/bin/env python3
"""Write an advisory brief for one district: published crop advice, with forecast context.

    python3 scripts/advisory_brief.py --place "Ahmedabad, Gujarat" --crop cotton --topic irrigation
    python3 scripts/advisory_brief.py --lat 23.02 --lon 72.57 --region Ahmedabad --state Gujarat \
        --crop cotton --stage "squaring" --mode decision_support --day 1

Published advice is quoted with its page, its printed issue date and its source. The forecast is
model output for a grid cell. Neither is a prescription, and the brief says what it does not know.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data.advisory import markdown  # noqa: E402
from weathergpt_data.gazetteer import Gazetteer, preferred_match  # noqa: E402
from weathergpt_data.transport import SourceError  # noqa: E402
from weathergpt_data.workspace import Workspace  # noqa: E402


def resolve(place):
    gazetteer = Gazetteer()
    name, _, state = str(place).partition(',')
    matches = gazetteer.search(name.strip(), state.strip())
    if not matches:
        raise SourceError('No indexed place matches: ' + str(place))
    chosen, why = preferred_match(matches)
    if chosen is None:
        raise SourceError('More than one place matches ' + str(place) + ' (' + why +
                          '). Add the state or district, or pass --region and --state.')
    admin1 = str(chosen.get('admin1') or '')
    return {'region': chosen.get('admin2') or chosen.get('name'), 'state': admin1.removeprefix('State of ').strip(),
            'latitude': chosen['coordinates']['latitude'], 'longitude': chosen['coordinates']['longitude'],
            'label': chosen.get('label'), 'why': why}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--place', help='a place name, optionally with its state: "Ahmedabad, Gujarat"')
    parser.add_argument('--region', help='the district whose published advice should be read')
    parser.add_argument('--state')
    parser.add_argument('--lat', type=float)
    parser.add_argument('--lon', type=float)
    parser.add_argument('--crop', default='')
    parser.add_argument('--stage', default='')
    parser.add_argument('--topic', default='general')
    parser.add_argument('--mode', default='source_lookup', choices=['source_lookup', 'decision_support'])
    parser.add_argument('--day', type=int, default=1)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--json', action='store_true')
    arguments = parser.parse_args()

    resolved = resolve(arguments.place) if arguments.place else {'region': arguments.region, 'state': arguments.state,
                                                                 'latitude': arguments.lat, 'longitude': arguments.lon,
                                                                 'label': arguments.region}
    if not resolved.get('region'):
        raise SystemExit('Give --place, or --region with the district whose advice should be read.')
    if resolved.get('latitude') is None or resolved.get('longitude') is None:
        raise SystemExit('A point is needed for the forecast context: give --place or --lat/--lon.')
    params = {'region': resolved['region'], 'state': resolved.get('state') or '',
              'lat': resolved['latitude'], 'lon': resolved['longitude'], 'crop': arguments.crop,
              'stage': arguments.stage, 'topic': arguments.topic, 'mode': arguments.mode, 'day': str(arguments.day)}
    workspace = Workspace()
    brief = workspace.advisory_brief(params)
    if arguments.json:
        import json
        print(json.dumps(brief, indent=2, ensure_ascii=False))
        return 0 if brief.get('status') == 'ok' else 1
    print('place: ' + str(resolved.get('label')) + ' (' + str(resolved.get('why') or 'as given') + ')')
    print('status: ' + str(brief.get('status')))
    if brief.get('status') == 'ok':
        print('edition: ' + str(brief['published_advice']['family']) + ' · passages ' + str(brief['published_advice']['matched']))
        print('forecast: ' + str(brief.get('forecast', {}).get('status')))
        print('brief id: sha256 ' + str(brief.get('brief_id'))[:16])
    else:
        print('why: ' + str(brief.get('why')))
    text = markdown(brief)
    edition_region = (brief.get('published_advice') or {}).get('region') or resolved['region']
    target = arguments.out or (ROOT / 'research' / 'implementation' / 'advisory-brief-20260915' /
                               ('brief-' + str(edition_region).replace(' ', '-').lower() + '-' +
                                (arguments.crop or 'general') + '-day' + str(arguments.day) + '.md'))
    if not target.is_absolute():
        target = ROOT / target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding='utf-8')
    print('written: ' + str(target.relative_to(ROOT)))
    return 0 if brief.get('status') == 'ok' else 1


if __name__ == '__main__':
    sys.exit(main())
