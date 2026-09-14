"""Vendored basemap build: structure, geometry, budgets and provenance.

Reads the committed build output offline. It does not re-run the network build,
and a pass here is not a claim about the source layers' authority.
"""
import json
import re
import unittest
from pathlib import Path

from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[1]
BUILDS = ROOT / 'data/processed/map-basemap'
ASSETS = ROOT / 'data/registry/assets.json'
LAYERS = {'land.geojson': 'polygon', 'states.geojson': 'polygon', 'districts.geojson': 'polygon',
          'basins.geojson': 'polygon', 'coast-zones.geojson': 'polygon', 'places.geojson': 'point'}
ALLOWED_PROPERTIES = {'land.geojson': {'k'}, 'states.geojson': {'k', 'n', 'c'}, 'districts.geojson': {'k', 'n', 's', 'p'},
                      'basins.geojson': {'k', 'n', 'b'}, 'coast-zones.geojson': {'k', 'n'},
                      'places.geojson': {'n', 't', 'a'}}
FORBIDDEN_PROPERTY = re.compile(r'colour|color|hazard|severity|day|warning|alert|level', re.I)
INDIA = (67.0, 5.0, 98.5, 38.5, 3.0)


def newest_build():
    builds = sorted(path for path in BUILDS.glob('basemap-v1-*') if path.is_dir())
    return builds[-1] if builds else None


class BasemapBuildTests(unittest.TestCase):
    def setUp(self):
        self.build = newest_build()
        if self.build is None:
            self.skipTest('no basemap build has been produced yet')
        self.manifest = json.loads((self.build / 'manifest.json').read_text())
        self.audit = json.loads((self.build / 'audit.json').read_text())
        self.layers = {name: json.loads((self.build / name).read_text()) for name in LAYERS}

    def test_build_is_complete_and_identified(self):
        for name in LAYERS:
            self.assertTrue((self.build / name).exists(), name + ' is missing')
        self.assertTrue((self.build / 'district-join.json').exists())
        self.assertEqual(self.manifest['build_id'], self.build.name)
        self.assertEqual(self.manifest['schema_version'], 'map-basemap-v1')
        self.assertEqual(self.audit['schema_version'], 'map-basemap-audit-v1')
        self.assertEqual(self.manifest['source_id'], 'S63')

    def test_every_feature_is_a_valid_geometry_in_range(self):
        for name, kind in LAYERS.items():
            for feature in self.layers[name]['features']:
                geometry = feature['geometry']
                if kind == 'polygon':
                    self.assertIn(geometry['type'], ('Polygon', 'MultiPolygon'), name)
                else:
                    self.assertEqual(geometry['type'], 'Point', name)
                parsed = shape(geometry)
                self.assertTrue(parsed.is_valid, name + ' carries an invalid geometry')
                self.assertFalse(parsed.is_empty, name + ' carries an empty geometry')
                minx, miny, maxx, maxy = parsed.bounds
                low_x, low_y, high_x, high_y, margin = INDIA
                self.assertGreater(minx, low_x - margin, name + ' escapes the longitude range')
                self.assertLess(maxx, high_x + margin, name + ' escapes the longitude range')
                self.assertGreater(miny, low_y - margin, name + ' escapes the latitude range')
                self.assertLess(maxy, high_y + margin, name + ' escapes the latitude range')

    def test_coordinates_are_bounded_in_precision(self):
        def digits(value):
            if isinstance(value, (int, float)):
                text = repr(float(value))
                return len(text.split('.')[1]) if '.' in text else 0
            if isinstance(value, list):
                return max([digits(item) for item in value] or [0])
            return 0
        recorded = set()
        for entry in self.audit['drawing'].values():
            recorded.update(entry.get('extra_precision') or [])
        for name, payload in self.layers.items():
            for feature in payload['features']:
                self.assertLessEqual(digits(feature['geometry']['coordinates']), 6, name)

    def test_no_warning_state_is_baked_into_the_geometry(self):
        for name, payload in self.layers.items():
            for feature in payload['features']:
                keys = set(feature['properties'])
                self.assertTrue(keys <= ALLOWED_PROPERTIES[name], name + ' has unexpected properties ' + str(sorted(keys)))
                for key in keys:
                    self.assertIsNone(FORBIDDEN_PROPERTY.search(key), name + ' bakes a warning field: ' + key)

    def test_budgets_and_manifest_bytes_match_the_files(self):
        for entry in self.manifest['layers']:
            path = self.build / entry['file']
            self.assertEqual(path.stat().st_size, entry['bytes'], entry['file'] + ' size drifted from the manifest')
            self.assertLessEqual(entry['bytes'], entry['budget_bytes'], entry['file'] + ' exceeds its budget')
            self.assertTrue(self.audit['budgets'][entry['file'].replace('.geojson', '')]['within_budget'])
        self.assertFalse(self.audit['budget_breaches'])
        self.assertLess(self.manifest['total_bytes'], 8_000_000, 'the vendored basemap must stay small enough to serve')

    def test_every_source_layer_records_a_digest(self):
        sources = self.manifest['sources']
        self.assertEqual(len(sources), 5)
        self.assertEqual({entry['layer'] for entry in sources},
                         {'imd:district_warnings_india', 'imd:india_high_2024', 'imd:India_State',
                          'imd:indian_river_basin', 'imd:coastal_sf'})
        for entry in sources:
            self.assertRegex(entry['sha256'], r'^[0-9a-f]{64}$')
            self.assertEqual(entry['source_id'], 'S63')
            self.assertTrue(entry['retrieved_at_utc'])

    def test_district_reconciliation_is_explicit(self):
        written = len(self.layers['districts.geojson']['features'])
        self.assertEqual(written, self.audit['district_polygons_written'])
        skipped = self.audit['skipped_without_a_district_name']
        self.assertEqual(written + len(skipped), self.audit['feature_counts']['districts'])
        for item in skipped:
            self.assertIn('obj_id', item)
            self.assertEqual(len(item['centroid']), 2)
        for entry in self.audit['duplicate_keys_resolved']:
            self.assertNotEqual(entry['key'], re.sub(r'[^A-Z]', '', str(entry['source_name']).upper()))

    def test_placeholder_geometry_is_labelled_not_hidden(self):
        flagged = [feature for feature in self.layers['districts.geojson']['features'] if feature['properties'].get('p')]
        recorded = self.audit.get('placeholder_geometry') or []
        self.assertEqual(len(flagged), len(recorded), 'every flagged placeholder must be recorded in the audit')
        for item in recorded:
            self.assertGreaterEqual(item['ratio'], 0.97)
            self.assertGreaterEqual(item['bbox_area_degrees'], 1.0)

    def test_join_covers_every_drawn_district(self):
        join = json.loads((self.build / 'district-join.json').read_text())
        self.assertEqual(join['schema_version'], 'district-join-v1')
        keys = {feature['properties']['k'] for feature in self.layers['districts.geojson']['features']}
        self.assertEqual(keys, set(join['districts']))
        attributed = [item for item in join['districts'].values() if item['state']]
        self.assertGreaterEqual(len(attributed) / len(keys), 0.95, 'state attribution fell below 95 percent')
        for item in join['districts'].values():
            self.assertGreaterEqual(item['overlap'], 0.0)
            self.assertLessEqual(item['overlap'], 1.0)
        self.assertEqual(len(attributed), self.audit['state_attribution']['attributed'])
        self.assertLessEqual(len(self.audit['state_attribution']['unattributed']), 40)

    def test_places_are_administrative_seats_only(self):
        codes = {feature['properties']['t'] for feature in self.layers['places.geojson']['features']}
        self.assertTrue(codes <= {'PPLC', 'PPLA', 'PPLA2'}, 'unexpected place classes: ' + str(sorted(codes)))
        self.assertEqual(len(self.layers['places.geojson']['features']), self.audit['feature_counts']['places'])

    def test_states_layer_matches_the_reported_count(self):
        self.assertEqual(len(self.layers['states.geojson']['features']), self.audit['feature_counts']['states'])
        for feature in self.layers['states.geojson']['features']:
            self.assertTrue(feature['properties']['n'])
            self.assertEqual(feature['properties']['k'], re.sub(r'[^A-Z]', '', feature['properties']['n'].upper()))

    def test_attribution_and_limitations_are_stated(self):
        self.assertIn('India Meteorological Department', self.manifest['attribution'])
        self.assertIn('GeoNames', self.manifest['attribution'])
        self.assertTrue(any('not a survey boundary' in note for note in self.manifest['limitations']))
        self.assertTrue(any('never baked' in note for note in self.audit['notes']))

    def test_build_files_are_registered_with_matching_hashes(self):
        import hashlib
        record = json.loads(ASSETS.read_text(encoding='utf-8'))
        tracked = {entry['path']: entry for entry in record['files']}
        for path in sorted(self.build.iterdir()):
            relative = str(path.relative_to(ROOT))
            self.assertIn(relative, tracked, relative + ' is not registered in assets.json')
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(tracked[relative]['sha256'], digest, relative + ' digest drifted from the registry')
            self.assertEqual(tracked[relative]['source_ids'], ['S63'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
