import json
import tempfile
import unittest
from pathlib import Path
from weathergpt_data.geography import Geography, geometry_status
from weathergpt_data.coverage import Coverage

EVIDENCE = {'source_id': 'test_fixture', 'sha256': 'a'*64, 'url': 'https://example.test/synthetic'}


class GeographyContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.g = Geography(Path(self.temp.name)/'geo.sqlite'); self.addCleanup(self.g.close)

    def add(self, **kw):
        values = dict(namespace='fixture', kind='district', source_code='123', version='v1',
                      label='Ahmedabad', locator='row1', evidence=EVIDENCE)
        values.update(kw); return self.g.add(**values)

    def test_names_do_not_merge_namespaces_or_entity_types(self):
        a = self.add(); b = self.add(namespace='other'); c = self.add(kind='city')
        self.assertEqual(len({a,b,c}), 3)
        self.assertEqual(self.g.resolve('Ahmedabad')['status'], 'needs_selection')
        self.assertEqual(self.g.mappings(a, '2026-09-12')['status'], 'unresolved')

    def test_versions_and_repeated_source_codes_preserved(self):
        self.add(); self.add(version='v2'); self.add(locator='row2', status='quarantined')
        self.assertEqual(self.g.db.execute('SELECT count(*) FROM entities').fetchone()[0], 3)
        self.assertEqual(len(self.g.resolve('Ahmedabad')['candidates']), 2)

    def test_reimport_idempotent_but_mutation_rejected(self):
        self.assertEqual(self.add(), self.add())
        with self.assertRaises(ValueError): self.add(label='Renamed')

    def test_unknown_dates_cannot_resolve_current_administration(self):
        self.add()
        self.assertEqual(self.g.resolve('Ahmedabad', on_date='2026-09-12')['status'], 'unresolved')
        self.assertEqual(self.g.resolve('Ahmedabad')['status'], 'single_source_candidate')

    def test_effective_boundary_is_half_open(self):
        old = self.add(effective_from='2000-01-01', effective_to='2025-10-02')
        new = self.add(version='v2', effective_from='2025-10-02')
        self.assertEqual(self.g.resolve('Ahmedabad',on_date='2025-10-01')['candidates'][0]['entity_id'], old)
        self.assertEqual(self.g.resolve('Ahmedabad',on_date='2025-10-02')['candidates'][0]['entity_id'], new)

    def test_historical_district_is_separate(self):
        self.add(kind='historical_district', effective_from='1901-01-01',effective_to='2011-01-01')
        self.assertEqual(self.g.resolve('Ahmedabad',kind='district')['status'], 'unresolved')

    def test_language_alias_preserved_without_invented_transliteration(self):
        self.add(aliases=[{'name':'અમદાવાદ', 'language':'gu'}])
        self.assertEqual(self.g.resolve('અમદાવાદ')['status'], 'single_source_candidate')
        self.assertEqual(self.g.resolve('Ahmadabad')['status'], 'unresolved')
        self.assertEqual(self.g.resolve('  AHMEDABAD  ')['status'], 'single_source_candidate')

    def test_candidate_mapping_not_operational(self):
        a = self.add(); b = self.add(namespace='lgd-fixture')
        self.g.relate(a,b,'same_identity',EVIDENCE)
        self.assertEqual(self.g.mappings(a,'2026-09-12')['status'], 'unresolved')
        with self.assertRaises(ValueError): self.g.relate(a,b,'same_identity',EVIDENCE,status='reviewed')

    def test_reviewed_mapping_dates_and_conflicts(self):
        a = self.add(); b = self.add(namespace='lgd-fixture'); c = self.add(namespace='lgd-fixture',source_code='456')
        self.g.relate(a,b,'same_identity',EVIDENCE,status='reviewed',reviewer='synthetic-test',effective_from='2020-01-01',effective_to='2025-01-01')
        self.assertEqual(self.g.mappings(a,'2025-01-01')['status'],'unresolved')
        self.g.relate(a,c,'same_identity',EVIDENCE,status='reviewed',reviewer='synthetic-test',effective_from='2024-01-01')
        self.assertEqual(self.g.mappings(a,'2024-01-01')['status'],'ambiguous')

    def test_airport_cannot_become_district_identity(self):
        a = self.add(); b = self.add(kind='airport')
        with self.assertRaises(ValueError): self.g.relate(a,b,'same_identity',EVIDENCE)

    def test_quarantined_mapping_rejected(self):
        a = self.add(status='quarantined'); b = self.add(namespace='target')
        with self.assertRaises(ValueError):
            self.g.relate(a,b,'same_identity',EVIDENCE,status='reviewed',reviewer='test',effective_from='2020-01-01')

    def test_invalid_geometry_retained_not_repaired(self):
        bowtie = {'type':'Polygon','coordinates':[[[0,0],[1,1],[0,1],[1,0],[0,0]]]}
        eid = self.add(geometry=bowtie,crs='EPSG:4326')
        self.assertEqual(self.g.get(eid)['geometry_status'],'invalid')
        self.assertEqual(self.g.get(eid)['geometry'],bowtie)
        self.assertEqual(self.g.areas_at(.5,.5,'fixture','v1')['excluded_records'],1)

    def test_shared_boundary_remains_ambiguous(self):
        for i in [0,1]:
            self.add(source_code=str(i),geometry={'type':'Polygon','coordinates':[[[i,0],[i+1,0],[i+1,1],[i,1],[i,0]]]},crs='EPSG:4326')
        result = self.g.areas_at(.5,1,'fixture','v1')
        self.assertEqual(result['status'],'ambiguous'); self.assertEqual(len(result['matches']),2)
        self.assertFalse(result['actionable_current_alerts'])
        self.assertEqual(self.g.areas_at(.5,.5,'fixture','v1')['status'],'source_polygon_match')

    def test_unknown_crs_and_empty_namespace_cannot_match(self):
        p = {'type':'Point','coordinates':[72,23]}
        self.assertEqual(geometry_status(p,None),'unsupported_crs')
        self.assertEqual(self.g.areas_at(23,72,'missing','v1')['status'],'unresolved')
        with self.assertRaises(ValueError): self.g.areas_at(float('nan'),72,'missing','v1')


class CoverageContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.c = Coverage(Path(self.temp.name)/'coverage.sqlite'); self.addCleanup(self.c.close)

    def record(self, **kw):
        values = dict(product='synthetic_forecast',entity_id='fixture-location',variable='temperature',source_id='fixture',
                      version='assessment-v1',window_start='2026-09-12T00:00:00Z',window_end='2026-09-13T00:00:00Z',
                      expected=24,fetched=24,validated=24,missing=0,quarantined=0,evidence=EVIDENCE,
                      assessed_at='2026-09-12T00:00:00Z')
        values.update(kw); return self.c.record(**values)

    def test_counts_do_not_establish_eligibility(self):
        r = self.c.assess(self.record(),'2026-09-12T01:00:00Z')
        self.assertFalse(r['eligible']); self.assertIn('Spatial applicability not validated',r['reasons'])

    def test_explicit_gates_and_freshness_expire_at_read_time(self):
        cid = self.record(spatial='validated',temporal='validated',policy='eligible',source_freshness='validated',
                          freshness_deadline='2026-09-12T02:00:00Z')
        self.assertTrue(self.c.assess(cid,'2026-09-12T01:00:00Z')['eligible'])
        self.assertFalse(self.c.assess(cid,'2026-09-12T02:00:00Z')['eligible'])
        self.assertFalse(self.c.assess(cid,'2026-09-11T23:00:00Z')['eligible'])

    def test_missing_not_all_clear(self):
        cid = self.record(product='official_warning',fetched=0,validated=0,missing=24)
        self.assertFalse(self.c.assess(cid,'2026-09-12T01:00:00Z')['eligible'])
        self.assertEqual(self.c.assess('absent','2026-09-12T01:00:00Z')['status'],'unavailable')

    def test_not_applicable_requires_explicit_reason_and_zero_expectations(self):
        with self.assertRaises(ValueError): self.record(expected=0,fetched=0,validated=0)
        cid = self.record(expected=0,fetched=0,validated=0,not_applicable_reason='Synthetic inland point: ocean wave product excluded by reviewed footprint')
        self.assertEqual(self.c.assess(cid,'2026-09-12T01:00:00Z')['status'],'not_applicable')
        with self.assertRaises(ValueError): self.record(not_applicable_reason='inland')

    def test_nulls_and_quarantines_count_separately(self):
        cid = self.record(validated=20,missing=3,quarantined=1)
        self.assertEqual(self.c.assess(cid,'2026-09-12T01:00:00Z')['coverage']['quarantined'],1)
        for kw in [dict(validated=25),dict(expected=True),dict(fetched=0),dict(missing=-1),dict(missing=1)]:
            with self.assertRaises(ValueError): self.record(version=str(kw),**kw)

    def test_interval_unknown_does_not_validate(self):
        with self.assertRaises(ValueError): self.record(window_start=None,window_end=None,temporal='validated')
        with self.assertRaises(ValueError): self.record(window_end='2026-09-11T00:00:00Z')
        with self.assertRaises(ValueError): self.record(window_start='2026-09-12T00:00:00')

    def test_immutable_idempotency_and_interval_normalization(self):
        cid = self.record(); self.assertEqual(cid,self.record())
        self.assertEqual(cid,self.record(window_start='2026-09-12T05:30:00+05:30',window_end='2026-09-13T05:30:00+05:30'))
        with self.assertRaises(ValueError): self.record(validated=23,missing=1)
        self.assertNotEqual(cid,self.record(version='v2',validated=23,missing=1))

    def test_source_hold_overrides_validated_counts(self):
        cid = self.record(policy='on_hold',spatial='validated',temporal='validated',source_freshness='validated',
                          freshness_deadline='2026-09-12T02:00:00Z')
        self.assertFalse(self.c.assess(cid,'2026-09-12T01:00:00Z')['eligible'])


class ReviewTracking(unittest.TestCase):
    def test_all_review_findings_tracked_once(self):
        import re
        root = Path(__file__).resolve().parents[1]
        review = root/'research/reviews/national-readiness-20260912/review.md'
        tracker = json.loads((root/'data/registry/hardening-progress.json').read_text())
        expected = set(re.findall(r'\| (R\d{2}) /',review.read_text()))
        ids = [x['id'] for x in tracker['findings']]
        self.assertEqual(set(ids),expected); self.assertEqual(len(ids),len(set(ids)))
        for row in tracker['findings']:
            self.assertTrue(row['next_action']); self.assertTrue(row['acceptance'])
            for path in row['evidence']: self.assertTrue((root/path).exists(),path)
        self.assertFalse(tracker['operational_ready'])


if __name__ == '__main__': unittest.main()
