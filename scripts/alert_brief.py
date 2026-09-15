#!/usr/bin/env python3
"""Write an alert brief for one place and one published warning day.

    python3 scripts/alert_brief.py --place "Patna, Bihar" --day 1
    python3 scripts/alert_brief.py --lat 25.594 --lon 85.136 --day 2 --out brief.md

The brief is composed only from evidence the workspace retrieves: the official district warning
day, the bulletin it came from, and the CAP relay reported separately. It is a record of what a
product published - not a warning issued here, not a forecast and not an all-clear.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data.alert_brief import markdown  # noqa: E402
from weathergpt_data.gazetteer import Gazetteer, preferred_match  # noqa: E402
from weathergpt_data.product_api import alert_brief_view  # noqa: E402
from weathergpt_data.transport import SourceError  # noqa: E402
from weathergpt_data.workspace import Workspace  # noqa: E402


def point_from_place(place):
    gazetteer = Gazetteer()
    name, _, state = str(place).partition(',')
    matches = gazetteer.search(name.strip(), state.strip())
    if not matches:
        raise SourceError('No indexed place matches: ' + str(place))
    chosen, why = preferred_match(matches)
    if chosen is None:
        raise SourceError('More than one place matches ' + str(place) + ' (' + why +
                          '). Add the state or district, or pass --lat and --lon.')
    return chosen['coordinates'], chosen['label'], why


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--place', help='a place name, optionally with its state: "Patna, Bihar"')
    parser.add_argument('--lat', type=float)
    parser.add_argument('--lon', type=float)
    parser.add_argument('--day', type=int, default=1, help='the published day number, 1 to 5')
    parser.add_argument('--out', type=Path, help='where to write the Markdown brief')
    parser.add_argument('--json', action='store_true', help='print the brief packet as JSON')
    arguments = parser.parse_args()

    if arguments.lat is None or arguments.lon is None:
        if not arguments.place:
            raise SystemExit('Give --place, or --lat and --lon.')
        coordinates, label, why = point_from_place(arguments.place)
        latitude, longitude = coordinates['latitude'], coordinates['longitude']
        print('place: ' + label + ' (' + why + ')')
    else:
        latitude, longitude = arguments.lat, arguments.lon

    workspace = Workspace()
    # The same route the page uses, so the CLI and the workspace cannot drift apart.
    view = workspace.product('/api/warnings/alert-brief',
                             {'lat': str(latitude), 'lon': str(longitude), 'day': str(arguments.day)})
    brief = view['data']
    if arguments.json:
        print(json.dumps(view, indent=2, ensure_ascii=False))
        return 0 if view['status'] == 'ok' else 1
    print('status: ' + view['status'])
    if view['status'] == 'ok':
        print('brief: ' + str(brief['status_line']))
        print('brief id: sha256 ' + str(brief.get('brief_id'))[:16])
    else:
        print('why: ' + str(brief.get('why')))
    text = markdown(brief)
    target = arguments.out or (ROOT / 'research' / 'implementation' / 'alert-brief-20260915' /
                               ('brief-' + str(min(round(latitude, 3), 99)) + '-' + str(min(round(longitude, 3), 999)) +
                                '-day' + str(arguments.day) + '.md'))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding='utf-8')
    print('written: ' + str(target.relative_to(ROOT)))
    return 0 if view['status'] == 'ok' else 1


if __name__ == '__main__':
    sys.exit(main())
