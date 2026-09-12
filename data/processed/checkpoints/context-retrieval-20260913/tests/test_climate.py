import csv
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from weathergpt_data.climate import ROOT,build,normalise,lookup

SOURCE=ROOT/'research/discovery/evidence/pasted-climate-check/rainfall.csv'

def fixture(change=None):
    reader=csv.DictReader(io.StringIO(SOURCE.read_text()))
    names=reader.fieldnames
    row=next(reader)
    if change: change(row)
    out=io.StringIO();writer=csv.DictWriter(out,fieldnames=names);writer.writeheader();writer.writerow(row)
    return out.getvalue().encode()

class ClimateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.out=build(output_root=cls.temp.name)
        cls.db=cls.out/'climate.sqlite'

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_published_annual_is_not_silently_repaired(self):
        result=lookup(self.db,'S25',2024)
        self.assertEqual(result['record']['value_decimal'],'1206.6')
        self.assertEqual(result['reconciliation']['computed_month_sum'],'1204.1')
        self.assertEqual(result['reconciliation']['difference_mm'],'2.5')
        self.assertIn('published_total_differs_from_month_sum',result['record']['quality_flags'])
        self.assertEqual(result['citation']['row'],125)

    def test_roundtrip_every_original_cell_from_sqlite(self):
        with sqlite3.connect(self.db) as con:
            for sid,file in [('S25','rainfall.csv'),('S26','temperature.csv')]:
                source=list(csv.DictReader(io.StringIO((SOURCE.parent/file).read_text())))
                records=con.execute('SELECT source_row,source_column,native_value FROM climate_records WHERE source_id=?',(sid,)).fetchall()
                self.assertEqual(len(records),2108)
                for row,column,native in records:self.assertEqual(native,source[row-2][column])

    def test_geography_and_missing_year_rejected(self):
        with self.assertRaisesRegex(ValueError,'All India'):lookup(self.db,'S25',2024,geography='Ahmedabad')
        with self.assertRaisesRegex(ValueError,'No published'):lookup(self.db,'S25',2025)
        with self.assertRaisesRegex(ValueError,'Unknown period'):lookup(self.db,'S25',2024,period='daily')

    def test_periods_are_distinct_and_calendar_boundaries_correct(self):
        annual=lookup(self.db,'S25',2024)['record']
        monsoon=lookup(self.db,'S25',2024,'JJAS')['record']
        self.assertEqual(annual['period_end_exclusive'],'2025-01-01')
        self.assertEqual(monsoon['period_start'],'2024-06-01')
        self.assertEqual(monsoon['period_end_exclusive'],'2024-10-01')
        self.assertNotEqual(annual['record_id'],monsoon['record_id'])

    def test_missing_month_does_not_become_zero(self):
        rows,checks=normalise(fixture(lambda r:r.update(Jan='')),'S25','fixture.csv')
        jan=next(r for r in rows if r['period_code']=='M01')
        self.assertIsNone(jan['value_decimal'])
        annual=next(c for c in checks if c['period_code']=='ANNUAL')
        self.assertIsNone(annual['computed_month_sum'])
        self.assertEqual(annual['status'],'not_comparable')

    def test_invalid_numeric_and_negative_rain_rejected(self):
        for value in ['NaN','Infinity','-1','oops']:
            with self.subTest(value=value),self.assertRaises(ValueError):
                normalise(fixture(lambda r:r.update(Jan=value)),'S25','fixture.csv')

    def test_units_geography_and_source_metadata_rejected(self):
        for change in [{'unit':'inch'},{'geography':'Ahmedabad'},{'source_id':'unknown'},{'fetched_at_utc':'2026-09-11T12:00:00'}]:
            with self.subTest(change=change),self.assertRaises(ValueError):
                normalise(fixture(lambda r:r.update(change)),'S25','fixture.csv')

    def test_schema_and_duplicate_year_rejected(self):
        with self.assertRaisesRegex(ValueError,'schema'):normalise(fixture().replace(b'Jan,',b'Unknown,'),'S25','fixture.csv')
        payload=fixture();lines=payload.splitlines(keepends=True)
        with self.assertRaisesRegex(ValueError,'duplicate year'):normalise(payload+lines[1],'S25','fixture.csv')

    def test_temperature_not_subject_to_rainfall_sum_rule(self):
        result=lookup(self.db,'S26',2024)
        self.assertEqual(result['record']['value_decimal'],'25.7431')
        self.assertIsNone(result['reconciliation'])
        self.assertEqual(result['record']['quality_flags'],[])

    def test_idempotent_build_and_output_corruption_detection(self):
        with tempfile.TemporaryDirectory() as d:
            out=build(output_root=d)
            self.assertEqual(build(output_root=d),out)
            with (out/'records.csv').open('a') as f:f.write('corruption\n')
            with self.assertRaisesRegex(ValueError,'modified'):build(output_root=d)

    def test_raw_asset_integrity_required(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for relative in ['data/registry/sources.json','data/registry/assets.json']:
                dest=root/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/relative).read_bytes())
            dest=root/SOURCE.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(SOURCE.read_bytes()+b'changed')
            with self.assertRaisesRegex(ValueError,'integrity'):build(root=root)

if __name__=='__main__':unittest.main()
