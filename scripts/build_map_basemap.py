#!/usr/bin/env python3
"""Build the vendored offline basemap from official IMD GeoServer layers.

One-time build. Writes simplified, provenance-carrying geometry so the served
application never contacts an external origin and never ships a raw layer.

Geometry sources, all official and all reachable without credentials:

  imd:district_warnings_india  764 district polygons carrying the day fields
  imd:india_high_2024          762 district outlines carrying state names
  imd:India_State               37 state outlines
  imd:indian_river_basin       220 sub-basin outlines
  imd:coastal_sf                17 named coastal zones
  local GeoNames extract        administrative place labels (CC BY 4.0)

District polygons come from the warning layer itself, so the map choropleth and
the warning table share one key space and cannot disagree. State names are
attributed geometrically from imd:india_high_2024, and every attribution records
its overlap ratio so a weak match is visible rather than silent.

Nothing is inferred or hidden. A district with no confident state match keeps a
null state, a feature with no district name is listed in the audit with its
source id, a repeated district name keeps a distinct key, and geometry that
cannot be repaired after rounding is dropped and counted.
"""
import argparse
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shapely.geometry import mapping, shape
from shapely.ops import unary_union
from shapely.strtree import STRtree
from shapely.validation import make_valid

from weathergpt_data.foundation import Foundation
from weathergpt_data.transport import digest, stamp, utcnow

OUT_ROOT = ROOT / 'data/processed/map-basemap'
ASSETS = ROOT / 'data/registry/assets.json'
GAZETTEER = ROOT / 'data/processed/geography/geonames-india-20260912/places.sqlite'
SOURCE_ID = 'S63'
WFS = 'https://reactjs.imd.gov.in/geoserver/wfs'
TTL = 30 * 24 * 3600
MAX_BYTES = 400_000_000
DIGITS = 4
JOIN_TOLERANCE = 0.01

TOLERANCE = {'states': 0.01, 'districts': 0.008, 'basins': 0.03, 'coast': 0.01, 'land': 0.02}
BUDGET_MB = {'land': 0.8, 'states': 1.5, 'districts': 3.5, 'basins': 2.5, 'coast-zones': 0.2, 'places': 0.6}
EXPECTED = {'districts': (764, 764), 'high': (762, 762), 'states': (37, 37), 'basins': (220, 220), 'coast': (17, 17)}
PLACE_FEATURES = ('PPLC', 'PPLA', 'PPLA2')


def params_for(layer, extra=None):
    params = {'service': 'WFS', 'version': '2.0.0', 'request': 'GetFeature', 'typeName': layer,
              'outputFormat': 'application/json', 'srsName': 'EPSG:4326'}
    if extra:
        params.update(extra)
    return params


def collection_parser(label, low, high):
    def parse(data, meta):
        if not isinstance(data, dict) or data.get('type') != 'FeatureCollection':
            raise ValueError(label + ': expected a FeatureCollection')
        features = data.get('features')
        if not isinstance(features, list) or not features:
            raise ValueError(label + ': no features')
        total = data.get('totalFeatures')
        if total is not None and int(total) != len(features):
            raise ValueError(label + ': truncated, ' + str(total) + ' reported vs ' + str(len(features)))
        if not low <= len(features) <= high:
            raise ValueError(label + ': ' + str(len(features)) + ' features outside ' + str((low, high)))
        for feature in features:
            if not isinstance(feature.get('geometry'), dict):
                raise ValueError(label + ': feature without geometry')
    return parse


def polygonal(geometry):
    if geometry.geom_type in ('Polygon', 'MultiPolygon'):
        return geometry
    if geometry.geom_type == 'GeometryCollection':
        parts = [part for part in geometry.geoms
                 if part.geom_type in ('Polygon', 'MultiPolygon') and not part.is_empty]
        if parts:
            return unary_union(parts)
    return None


def repair(geometry):
    if geometry is None or geometry.is_empty:
        return None
    attempts = [geometry]
    if not geometry.is_valid:
        attempts.append(make_valid(geometry))
        attempts.append(geometry.buffer(0))
    for attempt in attempts:
        candidate = polygonal(attempt)
        if candidate is not None and not candidate.is_empty and candidate.is_valid:
            return candidate
    return None


def simplify(geometry, tolerance):
    simplified = geometry.simplify(tolerance, preserve_topology=True)
    if simplified.is_empty or not simplified.is_valid:
        return geometry
    return simplified


def round_coords(value, digits):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return round(float(value), digits)
    if isinstance(value, (list, tuple)):
        return [round_coords(item, digits) for item in value]
    return value


def as_geometry(kind, payload):
    try:
        candidate = shape({'type': kind, 'coordinates': payload})
    except Exception:
        return None
    if candidate is None or candidate.is_empty or not candidate.is_valid:
        return None
    return candidate


def rounded(geometry, digits):
    # Whatever this returns has been parsed back and validated, because rounding and
    # repairing both change topology, and a repair may change the geometry type too.
    for precision in (digits, digits + 1, digits + 2):
        payload = round_coords(mapping(geometry)['coordinates'], precision)
        candidate = as_geometry(geometry.geom_type, payload)
        if candidate is not None:
            return candidate.geom_type, payload, precision
        broken = None
        try:
            broken = shape({'type': geometry.geom_type, 'coordinates': payload})
        except Exception:
            broken = None
        repaired = repair(broken) if broken is not None else None
        if repaired is None:
            continue
        for repair_precision in (precision, precision + 1):
            repaired_payload = round_coords(mapping(repaired)['coordinates'], repair_precision)
            settled = as_geometry(repaired.geom_type, repaired_payload)
            if settled is not None:
                return settled.geom_type, repaired_payload, repair_precision
    return None, None, None

def write_layer(path, features):
    text = json.dumps({'type': 'FeatureCollection', 'features': features}, separators=(',', ':'), ensure_ascii=False)
    path.write_text(text, encoding='utf-8')
    return len(text.encode('utf-8'))


def build_layer(items, tolerance, extra_properties):
    features = []
    dropped = []
    higher_precision = []
    for key, geometry, extra in items:
        cleaned = repair(geometry)
        if cleaned is None:
            dropped.append(key)
            continue
        cleaned = simplify(cleaned, tolerance)
        kind, coordinates, precision = rounded(cleaned, DIGITS)
        if coordinates is None:
            dropped.append(key)
            continue
        if precision != DIGITS:
            higher_precision.append(key)
        properties = {'k': key}
        properties.update(extra_properties(extra))
        features.append({'type': 'Feature', 'properties': properties,
                         'geometry': {'type': kind, 'coordinates': coordinates}})
    return features, dropped, higher_precision

def norm(value):
    return re.sub(r'[^A-Z]', '', str(value or '').upper())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUT_ROOT)
    parser.add_argument('--refresh', action='store_true', help='ignore the cached layer responses')
    parser.add_argument('--register', action='store_true', help='append the written files to data/registry/assets.json')
    arguments = parser.parse_args()

    foundation = Foundation()
    fetched = {}
    print('fetching official basemap layers')
    layers = (('districts', 'imd:district_warnings_india'), ('high', 'imd:india_high_2024'),
              ('states', 'imd:India_State'), ('basins', 'imd:indian_river_basin'), ('coast', 'imd:coastal_sf'))
    for name, layer in layers:
        low, high = EXPECTED[name]
        kwargs = {'ttl': TTL, 'max_bytes': MAX_BYTES}
        if arguments.refresh:
            kwargs['refresh'] = True
        data, meta = foundation.get(SOURCE_ID, WFS, params_for(layer), product_parser=collection_parser(name, low, high), **kwargs)
        fetched[name] = {'data': data, 'meta': meta, 'layer': layer}
        print('  {:<10} {:>5} features  sha {}'.format(name, len(data['features']), meta['sha256'][:12]))

    resolved = {}
    unusable = {}
    for name, entry in fetched.items():
        rows, bad = [], 0
        for feature in entry['data']['features']:
            geometry = repair(shape(feature['geometry']))
            if geometry is None:
                bad += 1
                continue
            rows.append((feature['properties'], geometry))
        resolved[name] = rows
        unusable[name] = bad

    high_items = [(norm(properties.get('district')), simplify(geometry, JOIN_TOLERANCE), properties)
                  for properties, geometry in resolved['high']]
    high_geometries = [item[1] for item in high_items]
    tree = STRtree(high_geometries)

    district_items = []
    attribution = {}
    skipped_unnamed = []
    duplicate_keys = []
    used_keys = set()
    for properties, geometry in resolved['districts']:
        raw = properties.get('District')
        key = norm(raw)
        obj_id = properties.get('Obj_id')
        if not key:
            centre = geometry.representative_point()
            skipped_unnamed.append({'obj_id': obj_id, 'source_locator': 'Obj_id ' + str(obj_id),
                                    'centroid': [round(centre.x, DIGITS), round(centre.y, DIGITS)]})
            continue
        if key in used_keys:
            key = key + '-' + str(obj_id if obj_id is not None else len(used_keys))
            duplicate_keys.append({'source_name': raw, 'key': key, 'obj_id': obj_id})
        used_keys.add(key)
        join_geometry = simplify(geometry, JOIN_TOLERANCE)
        best_index, best_area = None, 0.0
        for index in tree.query(join_geometry):
            try:
                overlap = join_geometry.intersection(high_geometries[index]).area
            except Exception:
                continue
            if overlap > best_area:
                best_area, best_index = overlap, index
        ratio = round(best_area / join_geometry.area, 3) if join_geometry.area else 0.0
        matched = high_items[best_index][2] if best_index is not None else None
        state = matched.get('state') if (matched and ratio >= 0.5) else None
        attribution[key] = {'district': raw, 'state': state, 'overlap': ratio,
                            'matched': matched.get('district') if matched else None}
        district_items.append((key, geometry, {'n': raw, 's': state}))

    land = unary_union([geometry for _, geometry in resolved['high']])
    states = [(norm(properties.get('stname')), geometry, properties) for properties, geometry in resolved['states']]
    basins = [(norm(properties.get('SUBBASIN') or properties.get('River_Basi')), geometry,
               {'n': properties.get('SUBBASIN') or properties.get('River_Basi'), 'b': properties.get('BASIN')})
              for properties, geometry in resolved['basins']]
    coast = [(norm(properties.get('det_name')), geometry, {'n': properties.get('det_name')})
             for properties, geometry in resolved['coast']]

    connection = sqlite3.connect(GAZETTEER)
    place_features = []
    for name, latitude, longitude, feature, admin1 in connection.execute(
            'select name, latitude, longitude, feature, admin1 from places where feature in (?,?,?) order by feature, name',
            PLACE_FEATURES):
        place_features.append({'type': 'Feature', 'properties': {'n': name, 't': feature, 'a': admin1},
                               'geometry': {'type': 'Point',
                                            'coordinates': [round(float(longitude), DIGITS), round(float(latitude), DIGITS)]}})
    connection.close()

    build_material = json.dumps(sorted((name, entry['meta']['sha256']) for name, entry in fetched.items())).encode()
    build_id = 'basemap-v1-' + digest(build_material)[:12]
    target = arguments.output / build_id
    target.mkdir(parents=True, exist_ok=True)

    drawn = {}
    written = {}
    district_features, dropped_districts, precise_districts = build_layer(
        district_items, TOLERANCE['districts'], lambda extra: {'n': extra['n'], 's': extra['s']})
    drawn['districts'] = {'dropped': dropped_districts, 'extra_precision': precise_districts}
    written['places'] = write_layer(target / 'places.geojson', place_features)
    state_features, dropped_states, precise_states = build_layer(
        states, TOLERANCE['states'], lambda extra: {'n': extra.get('stname'), 'c': extra.get('stcode11')})
    drawn['states'] = {'dropped': dropped_states, 'extra_precision': precise_states}
    written['states'] = write_layer(target / 'states.geojson', state_features)
    basin_features, dropped_basins, precise_basins = build_layer(
        basins, TOLERANCE['basins'], lambda extra: {'n': extra['n'], 'b': extra['b']})
    drawn['basins'] = {'dropped': dropped_basins, 'extra_precision': precise_basins}
    written['basins'] = write_layer(target / 'basins.geojson', basin_features)
    coast_features, dropped_coast, precise_coast = build_layer(coast, TOLERANCE['coast'], lambda extra: {'n': extra['n']})
    drawn['coast-zones'] = {'dropped': dropped_coast, 'extra_precision': precise_coast}
    written['coast-zones'] = write_layer(target / 'coast-zones.geojson', coast_features)
    land_features, dropped_land, precise_land = build_layer([('india', land, {})], TOLERANCE['land'], lambda extra: {})
    drawn['land'] = {'dropped': dropped_land, 'extra_precision': precise_land}
    written['land'] = write_layer(target / 'land.geojson', land_features)

    # A source placeholder is a bounding box, not a coastline: detect it, label it on
    # the feature, and record it, so the map never draws a rectangle as a district.
    placeholders = []
    for feature in district_features:
        area = shape(feature['geometry'])
        minx, miny, maxx, maxy = area.bounds
        box = (maxx - minx) * (maxy - miny)
        if box >= 1.0 and area.area / box >= 0.97:
            feature['properties']['p'] = 1
            placeholders.append({'district': feature['properties'].get('n'),
                                 'bbox': [round(value, 2) for value in area.bounds],
                                 'bbox_area_degrees': round(box, 2),
                                 'ratio': round(area.area / box, 3)})

    written['districts'] = write_layer(target / 'districts.geojson', district_features)
    join_path = target / 'district-join.json'
    join_text = json.dumps({'schema_version': 'district-join-v1', 'source_layer': fetched['districts']['layer'],
                            'attribution_layer': fetched['high']['layer'], 'districts': attribution},
                           separators=(',', ':'), ensure_ascii=False)
    join_path.write_text(join_text, encoding='utf-8')

    budgets = {}
    breaches = []
    for name, size in written.items():
        limit = int(BUDGET_MB[name] * 1_000_000)
        budgets[name] = {'bytes': size, 'limit_bytes': limit, 'within_budget': size <= limit}
        if size > limit:
            breaches.append(name)

    rows = list(attribution.values())
    created = stamp(utcnow())
    audit = {
        'schema_version': 'map-basemap-audit-v1',
        'build_id': build_id,
        'created_at_utc': created,
        'feature_counts': {name: len(entry['data']['features']) for name, entry in fetched.items()} | {'places': len(place_features)},
        'district_polygons_written': len(district_features),
        'expected_counts': {name: EXPECTED[name][0] for name in EXPECTED},
        'unusable_source_geometry': unusable,
        'skipped_without_a_district_name': skipped_unnamed,
        'duplicate_keys_resolved': duplicate_keys,
        'placeholder_geometry': placeholders,
        'drawing': drawn,
        'state_attribution': {
            'districts': len(rows),
            'attributed': sum(1 for item in rows if item['state']),
            'unattributed': sorted(item['district'] for item in rows if not item['state'])[:40],
            'overlap_below_half': sum(1 for item in rows if item['overlap'] < 0.5),
            'exact_name_matches': sum(1 for item in rows if item['matched'] and norm(item['matched']) == norm(item['district'])),
            'overlap_is_approximate': 'computed on geometry simplified by the join tolerance',
        },
        'join_tolerance_degrees': JOIN_TOLERANCE,
        'budgets': budgets,
        'budget_breaches': breaches,
        'place_features': {code: sum(1 for feature in place_features if feature['properties']['t'] == code) for code in PLACE_FEATURES},
        'tolerances': TOLERANCE,
        'coordinate_digits': DIGITS,
        'notes': ['District geometry comes from the warning layer so the map and the warning table share one key space.',
                  'State names are attributed geometrically with a recorded overlap ratio; a null state means no confident match.',
                  'A district missing from this build is caused by a source feature without a district name, and is listed above.',
                  'A placeholder polygon is a source bounding box rather than a coastline; it is labelled p=1 and listed in placeholder_geometry.',
                  'No basemap imagery, third-party cartography or external tile origin is used.',
                  'Warning colour is applied at render time and is never baked into this geometry.'],
    }
    (target / 'audit.json').write_text(json.dumps(audit, indent=2, ensure_ascii=False) + chr(10), encoding='utf-8')

    manifest = {
        'schema_version': 'map-basemap-v1',
        'build_id': build_id,
        'created_at_utc': created,
        'source_id': SOURCE_ID,
        'service': WFS,
        'layers': [{'file': name + '.geojson', 'bytes': size, 'budget_bytes': budgets[name]['limit_bytes']}
                   for name, size in sorted(written.items())],
        'join_file': join_path.name,
        'join_bytes': len(join_text.encode('utf-8')),
        'total_bytes': sum(written.values()) + len(join_text.encode('utf-8')),
        'sources': [{'layer': entry['layer'], 'sha256': entry['meta']['sha256'],
                     'retrieved_at_utc': entry['meta']['retrieved_at_utc'], 'source_id': SOURCE_ID}
                    for name, entry in sorted(fetched.items())],
        'attribution': 'Geometry: India Meteorological Department GeoServer, terms unresolved, local prototype use. Places: GeoNames, CC BY 4.0.',
        'limitations': ['Simplified for display; not a survey boundary and not an LGD crosswalk.',
                        'Place labels are GeoNames administrative seats, not an official settlement register.'],
    }
    (target / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + chr(10), encoding='utf-8')

    print()
    print('build_id         ', build_id)
    print('target           ', target.relative_to(ROOT))
    print('total bytes      ', '{:,}'.format(manifest['total_bytes']))
    for name, size in sorted(written.items()):
        print('  {:<14} {:>10,} bytes'.format(name, size))
    print('district polygons', len(district_features), 'of', len(fetched['districts']['data']['features']))
    print('skipped unnamed  ', len(skipped_unnamed))
    print('state attributed ', audit['state_attribution']['attributed'], '/', audit['state_attribution']['districts'])
    print('exact name match ', audit['state_attribution']['exact_name_matches'])

    if arguments.register:
        record = json.loads(ASSETS.read_text(encoding='utf-8'))
        by_path = {entry['path']: entry for entry in record['files']}
        added = updated = 0
        for path in sorted(target.iterdir()):
            relative = str(path.relative_to(ROOT))
            entry = {'path': relative, 'source_ids': [SOURCE_ID], 'bytes': path.stat().st_size,
                     'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
            if relative in by_path:
                if by_path[relative] != entry:
                    by_path[relative] = entry
                    updated += 1
            else:
                by_path[relative] = entry
                added += 1
        record['files'] = sorted(by_path.values(), key=lambda item: item['path'])
        ASSETS.write_text(json.dumps(record, indent=2, ensure_ascii=False) + chr(10), encoding='utf-8')
        print('registered       ', added, 'new,', updated, 'updated hashes')
    if breaches:
        print('BUDGET BREACH    ' + ', '.join(breaches), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
