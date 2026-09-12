"""Exercise a fresh full district build and rejection without touching frozen inputs."""
import csv
import io
import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from weathergpt_data import districts
from weathergpt_data.transport import digest,SourceError

ROOT=Path(__file__).resolve().parents[1]

class DistrictRebuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
        dest=cls.root/'data/raw/imports/2026-09-11/states'
        shutil.copytree(ROOT/'data/raw/imports/2026-09-11/states',dest)
        manifest=cls.root/'data/registry/assets.json';manifest.parent.mkdir(parents=True)
        manifest.write_bytes((ROOT/'data/registry/assets.json').read_bytes())
        cls.registry=manifest;cls.file=sorted(dest.glob('*.csv'))[0]
        cls.original=cls.file.read_bytes();cls.original_registry=manifest.read_bytes()

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def tearDown(self):
        self.file.write_bytes(self.original);self.registry.write_bytes(self.original_registry)

    def test_fresh_build_exact_rows_missingness_and_idempotence(self):
        with patch.object(districts,'ROOT',self.root):
            out=districts.build();self.assertEqual(districts.build(),out)
            audit=json.loads((out/'audit.json').read_text())
            self.assertEqual((audit['rows'],audit['series'],audit['missing_month_cells']),(60568,640,15817))
            with sqlite3.connect(out/'districts.sqlite') as db:
                row=db.execute("SELECT state,district,year FROM rainfall WHERE json_extract(payload,'$.jan_mm')='' LIMIT 1").fetchone()
            answer=districts.lookup(out/'districts.sqlite',*row,period='jan')
            self.assertEqual(answer['status'],'no_data');self.assertIsNone(answer['value_decimal'])
            (out/'audit.json').write_text('{}')
            with self.assertRaisesRegex(SourceError,'Modified district output'):districts.build()

    def test_registered_source_hash_required(self):
        self.file.write_bytes(self.original+b'corruption')
        with patch.object(districts,'ROOT',self.root),self.assertRaisesRegex(SourceError,'hash mismatch'):districts.build()

    def test_bad_numeric_input_rolls_back_temporary_build(self):
        reader=csv.DictReader(io.StringIO(self.original.decode('utf-8-sig')));rows=list(reader);rows[0]['jan_mm']='-1'
        buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=reader.fieldnames);writer.writeheader();writer.writerows(rows)
        self.file.write_text(buf.getvalue())
        registry=json.loads(self.original_registry)
        for item in registry['files']:
            if item['path']==str(self.file.relative_to(self.root)):item['sha256']=digest(self.file.read_bytes())
        self.registry.write_text(json.dumps(registry))
        with patch.object(districts,'ROOT',self.root),self.assertRaisesRegex(SourceError,'Invalid district rainfall'):districts.build()
        self.assertFalse(list((self.root/'data/processed/districts').glob('.building-*')))

    def test_missing_source_file_rejected(self):
        self.file.unlink()
        with patch.object(districts,'ROOT',self.root),self.assertRaisesRegex(SourceError,'32 registered'):districts.build()

if __name__=='__main__':unittest.main()
